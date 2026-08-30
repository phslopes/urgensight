import pytest
from httpx import ASGITransport, AsyncClient

from src.app import app


@pytest.fixture
def mock_pipeline():
    """Pipeline scikit-learn deterministico para testes."""

    class _MockPipeline:
        def predict(self, texts):
            return ["normal"] * len(texts)

    return _MockPipeline()


@pytest.fixture
def mock_app_with_model(monkeypatch, mock_pipeline):
    """Configura o app FastAPI com modelo carregado."""
    monkeypatch.setattr("src.app.model_pipeline", mock_pipeline)
    monkeypatch.setattr("src.app._load_model", lambda path: mock_pipeline)
    return mock_pipeline


@pytest.fixture
async def async_client():
    """Cliente HTTP assincrono para rotas FastAPI usando ASGITransport."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
