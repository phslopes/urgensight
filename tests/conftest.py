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
def real_model(monkeypatch, mock_pipeline):
    """Estado pos-startup simulado: modelo carregado com sucesso.

    O TestClient dispara o lifespan, que tentaria carregar o modelo real
    de ``models/model.pkl``. Como o teste quer controlar o estado
    explicitamente, _load_model e substituido pelo mock ANTES do startup.
    """
    monkeypatch.setattr("src.app.model_pipeline", mock_pipeline)
    monkeypatch.setattr("src.app._load_model", lambda path: mock_pipeline)
    return mock_pipeline


@pytest.fixture
def broken_model(monkeypatch):
    """Estado pos-startup simulado: falha ao carregar o modelo.

    Configura o estado como "nao carregado" e impede que o lifespan
    recarregue o modelo real, simulando o cenario de arquivo ausente ou
    incompativel (o codigo de producao logaria a falha e seguiria com
    ``model_pipeline = None``).
    """
    monkeypatch.setattr("src.app.model_pipeline", None)

    def _raise(path):
        raise FileNotFoundError(f"Modelo nao encontrado: {path}")

    monkeypatch.setattr("src.app._load_model", _raise)


@pytest.fixture
async def async_client():
    """Cliente HTTP assincrono para rotas FastAPI usando ASGITransport."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
