"""Testes do backend de inferencia ONNX opcional da API (Etapa 4).

Cobre a selecao de backend via a variavel de ambiente ``MODEL_BACKEND``
em ``src/app.py`` (ver docstring do modulo e ADR-0011). Pulado
automaticamente se ``onnxruntime`` (grupo opcional ``api-onnx``/
``optimization``) ou ``models/model.onnx`` nao estiverem disponiveis --
nao bloqueia o job de teste padrao do CI, que roda so o grupo ``dev``.
"""

from pathlib import Path

import pytest

pytest.importorskip(
    "onnxruntime", reason="onnxruntime nao instalado (grupo opcional 'api-onnx')"
)

from fastapi.testclient import TestClient  # noqa: E402

import src.app as app_module  # noqa: E402
from src.app import app  # noqa: E402
from src.onnx_inference import OnnxPipeline  # noqa: E402

ONNX_PATH = Path("models/model.onnx")

requires_onnx_model = pytest.mark.skipif(
    not ONNX_PATH.exists(),
    reason=f"{ONNX_PATH} nao encontrado -- rode "
    "`python -m scripts.convert_to_onnx` antes.",
)


@requires_onnx_model
def test_load_model_returns_onnx_pipeline_when_backend_is_onnx(monkeypatch):
    monkeypatch.setattr(app_module, "MODEL_BACKEND", "onnx")
    pipeline = app_module._load_model(ONNX_PATH)
    assert isinstance(pipeline, OnnxPipeline)


def test_load_model_returns_sklearn_pipeline_by_default(monkeypatch):
    """MODEL_BACKEND ausente/"sklearn" preserva o comportamento da Etapa 2."""
    monkeypatch.setattr(app_module, "MODEL_BACKEND", "sklearn")
    called_with = {}

    def _fake_load_pipeline(path):
        called_with["path"] = path
        return "fake-sklearn-pipeline"

    monkeypatch.setattr("src.train.load_pipeline", _fake_load_pipeline)

    result = app_module._load_model(app_module.MODEL_PATH)

    assert result == "fake-sklearn-pipeline"
    assert called_with["path"] == app_module.MODEL_PATH


@requires_onnx_model
def test_predict_endpoint_works_with_onnx_backend(monkeypatch):
    monkeypatch.setattr(app_module, "MODEL_BACKEND", "onnx")
    monkeypatch.setattr(app_module, "ACTIVE_MODEL_PATH", ONNX_PATH)

    with TestClient(app) as client:
        response = client.post(
            "/predict",
            json={
                "text": (
                    "Severe chest pain with dyspnea and diaphoresis, ECG "
                    "shows ST elevation, suspect acute myocardial infarction."
                )
            },
        )

    assert response.status_code == 200
    assert response.json()["prediction"] in {"normal", "atencao", "urgente"}
