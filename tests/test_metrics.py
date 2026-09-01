"""Testes da instrumentacao Prometheus da API (Etapa 3).

As metricas do prometheus_client sao globais por processo e acumulam entre
testes, entao todas as assercoes leem valores por diferenca (antes/depois)
em vez de assumir zero inicial.
"""

from fastapi.testclient import TestClient

from src.app import app
from src.metrics import MODEL_LOADED, PREDICTIONS_TOTAL, REQUEST_LATENCY, REQUESTS_TOTAL


def sample_value(metric, name: str, labels: dict) -> float:
    """Le o valor de uma amostra especifica de uma metrica (0.0 se ausente)."""
    for family in metric.collect():
        for sample in family.samples:
            if sample.name == name and sample.labels == labels:
                return sample.value
    return 0.0


def test_metrics_endpoint_returns_prometheus_format(real_model):
    with TestClient(app) as client:
        response = client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "http_requests_total" in response.text


def test_predict_increments_request_counter(real_model):
    labels = {"method": "POST", "path": "/predict", "status": "200"}
    before = sample_value(REQUESTS_TOTAL, "http_requests_total", labels)

    with TestClient(app) as client:
        client.post("/predict", json={"text": "Paciente com dor toracica."})

    after = sample_value(REQUESTS_TOTAL, "http_requests_total", labels)
    assert after == before + 1


def test_latency_histogram_records_observation(real_model):
    labels = {"method": "POST", "path": "/predict"}
    before = sample_value(REQUEST_LATENCY, "http_request_latency_seconds_count", labels)

    with TestClient(app) as client:
        client.post("/predict", json={"text": "Paciente estavel."})

    after = sample_value(REQUEST_LATENCY, "http_request_latency_seconds_count", labels)
    assert after == before + 1


def test_metrics_and_health_are_excluded_from_business_metrics(real_model):
    health_labels = {"method": "GET", "path": "/health", "status": "200"}
    metrics_labels = {"method": "GET", "path": "/metrics", "status": "200"}

    with TestClient(app) as client:
        client.get("/health")
        client.get("/metrics")

    assert sample_value(REQUESTS_TOTAL, "http_requests_total", health_labels) == 0.0
    assert sample_value(REQUESTS_TOTAL, "http_requests_total", metrics_labels) == 0.0


def test_model_loaded_gauge_is_one_when_model_loaded(real_model):
    with TestClient(app) as client:
        client.get("/health")

    assert sample_value(MODEL_LOADED, "model_loaded", {}) == 1.0


def test_model_loaded_gauge_is_zero_when_model_missing(broken_model):
    with TestClient(app, raise_server_exceptions=False) as client:
        client.get("/health")

    assert sample_value(MODEL_LOADED, "model_loaded", {}) == 0.0


def test_predictions_total_increments_for_predicted_class(real_model):
    labels = {"urgency": "normal"}
    before = sample_value(PREDICTIONS_TOTAL, "predictions_total", labels)

    with TestClient(app) as client:
        client.post("/predict", json={"text": "Paciente sem queixas."})

    after = sample_value(PREDICTIONS_TOTAL, "predictions_total", labels)
    assert after == before + 1
