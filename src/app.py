"""API REST de inferencia do modelo de triagem de laudos medicos (UrgenSight).

Etapa 2: expoe o pipeline de ML serializado em ``models/model.pkl``
(TF-IDF + classificador, ver ``src/train.py``) via endpoint de predicao.
O modelo e carregado em memoria uma unica vez, na inicializacao da
aplicacao (lifespan), e reutilizado por todas as requisicoes.

Se o modelo nao puder ser carregado, a API inicia mesmo assim: o health
check passa a reportar ``503 Service Unavailable`` (modelo indisponivel)
e ``POST /predict`` responde ``503`` ate que um modelo valido esteja
presente e a aplicacao seja reiniciada.

Uso:
    uvicorn src.app:app --host 0.0.0.0 --port 8000

Documentacao interativa (Swagger UI): http://localhost:8000/docs
Contrato formal da API: docs/api_contract.md
"""

import logging
from contextlib import asynccontextmanager
from enum import Enum
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.metrics import setup_metrics

logger = logging.getLogger(__name__)

# Caminho absoluto ancorado na raiz do projeto (dois niveis acima deste
# arquivo: src/app.py -> src/ -> raiz). Independe do diretorio de trabalho
# de onde o uvicorn foi iniciado.
MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "model.pkl"


class PredictionLabel(str, Enum):
    """Classes de urgencia suportadas pelo modelo de triagem."""

    NORMAL = "normal"
    ATENCAO = "atencao"
    URGENTE = "urgente"


class PredictRequest(BaseModel):
    """Payload de entrada do endpoint de predicao."""

    text: str = Field(
        ...,
        min_length=1,
        description="Texto do laudo medico a ser classificado.",
        json_schema_extra={
            "example": "Paciente apresenta dor toracica intensa e dispneia."
        },
    )


class PredictResponse(BaseModel):
    """Resposta do endpoint de predicao."""

    prediction: PredictionLabel = Field(
        ...,
        description="Classe de urgencia prevista: normal, atencao ou urgente.",
        json_schema_extra={"example": "normal"},
    )


class HealthResponse(BaseModel):
    """Resposta do endpoint de health check."""

    status: str = Field(
        default="ok",
        description="Status de saude da API.",
        json_schema_extra={"example": "ok"},
    )
    model_loaded: bool = Field(
        ...,
        description="Indica se o modelo de ML esta carregado em memoria.",
        json_schema_extra={"example": True},
    )


# Estado em nivel de modulo, preenchido pelo lifespan na inicializacao.
# None = modelo nao carregado (arquivo ausente ou invalido).
model_pipeline = None


def _load_model(path: Path):
    """Carrega o pipeline serializado via joblib. Lanca excecao se invalido."""
    from src.train import load_pipeline

    return load_pipeline(path)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida: carrega o modelo uma vez no startup.

    Falhas de carregamento (arquivo ausente, pickle corrompido, versao
    incompativel de sklearn/dill) nao impedem a API de iniciar: o estado
    fica com ``model_pipeline = None`` e os endpoints respondem 503.
    """
    global model_pipeline
    try:
        model_pipeline = _load_model(MODEL_PATH)
        logger.info("Modelo carregado com sucesso: %s", MODEL_PATH)
    except Exception as exc:
        model_pipeline = None
        logger.error(
            "Falha ao carregar o modelo em %s: %s", MODEL_PATH, exc, exc_info=True
        )
    yield
    model_pipeline = None


app = FastAPI(
    title="UrgenSight API",
    description=(
        "API de triagem automatica de laudos medicos. "
        "Classifica o texto do laudo em tres niveis de urgencia: "
        "normal, atencao ou urgente. "
        "Inferencia via pipeline TF-IDF + classificador (models/model.pkl)."
    ),
    version="0.2.0",
    lifespan=lifespan,
)
setup_metrics(app)


def _require_model():
    """Retorna o pipeline carregado ou levanta HTTPException 503."""
    if model_pipeline is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Modelo de ML indisponivel. "
                "Verifique se models/model.pkl existe e e compativel "
                "com as versoes de requirements.txt."
            ),
        )
    return model_pipeline


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    tags=["monitoramento"],
)
def health() -> HealthResponse:
    """Retorna o status de saude da API, incluindo o estado do modelo.

    Responde ``200 {"status":"ok","model_loaded":true}`` somente quando a
    API esta saudavel E o modelo esta carregado; caso contrario ``503``
    com corpo ``{"detail": "Modelo de ML indisponivel."}``.
    """
    if model_pipeline is None:
        raise HTTPException(status_code=503, detail="Modelo de ML indisponivel.")
    return HealthResponse(status="ok", model_loaded=True)


@app.post(
    "/predict",
    response_model=PredictResponse,
    summary="Classifica a urgencia de um laudo",
    tags=["inferencia"],
    responses={
        503: {"description": "Modelo de ML indisponivel."},
    },
)
def predict(request: PredictRequest) -> PredictResponse:
    """Classifica o texto do laudo em uma das classes de urgencia.

    Executa a inferencia real com o pipeline carregado no startup. Se o
    modelo nao estiver disponivel, responde ``503 Service Unavailable``.
    """
    pipeline = _require_model()
    prediction = pipeline.predict([request.text])[0]
    return PredictResponse(prediction=PredictionLabel(prediction))
