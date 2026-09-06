"""Testes automatizados da API UrgenSight (Etapa 2).

Cobre os 4 cenarios minimos exigidos pelo Code Review:
1. GET /health retorna 200 quando o modelo esta carregado.
2. POST /predict retorna 200 e uma predicao valida com payload correto.
3. POST /predict retorna 422 com payload invalido (validacao Pydantic).
4. POST /predict retorna 503 quando o modelo nao esta carregado.

Os testes usam ``monkeypatch`` para isolar o ciclo de vida do modelo sem
depender de ``models/model.pkl`` real, garantindo execucao rapida e
deterministica em CI. Para os cenarios "modelo nao carregado", a fixture
``broken_model`` impede que o lifespan recarregue o modelo real no
startup do TestClient, simulando falha de carga (ex.: arquivo ausente).
"""

from fastapi.testclient import TestClient

from src.app import app


def test_health_returns_200_when_model_loaded(real_model):
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "model_loaded": True}


def test_health_returns_503_when_model_not_loaded(broken_model):
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"detail": "Modelo de ML indisponivel."}


def test_predict_returns_200_with_valid_payload(real_model):
    with TestClient(app) as client:
        response = client.post(
            "/predict",
            json={"text": "Paciente com dor toracica intensa."},
        )

    assert response.status_code == 200
    assert response.json() == {"prediction": "normal"}


def test_predict_returns_422_with_invalid_payload(real_model):
    with TestClient(app) as client:
        response = client.post("/predict", json={})

    assert response.status_code == 422


def test_predict_returns_422_with_empty_text(real_model):
    with TestClient(app) as client:
        response = client.post("/predict", json={"text": ""})

    assert response.status_code == 422


def test_predict_returns_503_when_model_not_loaded(broken_model):
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/predict",
            json={"text": "Texto qualquer."},
        )

    assert response.status_code == 503
    assert "Modelo de ML indisponivel" in response.json()["detail"]


def test_predict_rejects_unknown_model_output(monkeypatch):
    """Se o pipeline devolver uma classe fora do Enum, a API responde 500."""

    class _InvalidPipeline:
        def predict(self, texts):
            return ["classe_inexistente"]

    monkeypatch.setattr("src.app.model_pipeline", _InvalidPipeline())
    monkeypatch.setattr("src.app._load_model", lambda path: _InvalidPipeline())

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/predict", json={"text": "Texto."})

    assert response.status_code == 500
