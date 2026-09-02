"""Instrumentacao Prometheus da API UrgenSight (Etapa 3).

Modulo isolado que concentra as metricas expostas em ``GET /metrics``, no
formato de exposicao do Prometheus. ``src/app.py`` apenas registra
``setup_metrics(app)`` e atualiza as metricas de dominio nos pontos
relevantes, sem absorver a preocupacao transversal.

Decisoes registradas em docs/ai/adr/0004-instrumentacao-e-contrato-de-metricas.md
"""

import time

from fastapi import FastAPI, Request
from prometheus_client import Counter, Gauge, Histogram, make_asgi_app

# Rotas de infraestrutura ficam fora das metricas de negocio. O scrape do
# Prometheus (15s) injetaria ~240 req/h e o healthcheck do Docker (30s) mais
# ~120 req/h: os paineis de total e throughput passariam a medir o proprio
# monitoramento em vez do trafego de inferencia.
EXCLUDED_PATHS = frozenset({"/metrics", "/health"})

# Buckets calibrados ao baseline real de docs/baseline_latency.md
# (p50 2,4ms | p95 5,8ms | p99 21,2ms). Os buckets padrao das aulas comecam
# em 0.01s e colocariam quase toda a massa no primeiro bucket, inutilizando
# histogram_quantile.
LATENCY_BUCKETS = (0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)

REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total de requisicoes HTTP recebidas pela API",
    ["method", "path", "status"],
)

REQUEST_LATENCY = Histogram(
    "http_request_latency_seconds",
    "Latencia das requisicoes HTTP em segundos",
    ["method", "path"],
    buckets=LATENCY_BUCKETS,
)

MODEL_LOADED = Gauge(
    "model_loaded",
    "Indica se o modelo de ML esta carregado em memoria (1) ou nao (0)",
)

PREDICTIONS_TOTAL = Counter(
    "predictions_total",
    "Total de predicoes realizadas, por classe de urgencia",
    ["urgency"],
)


def setup_metrics(app: FastAPI) -> None:
    """Registra o middleware de metricas e monta o endpoint /metrics."""

    @app.middleware("http")
    async def _metrics_middleware(request: Request, call_next):
        path = request.url.path
        # O Mount() do /metrics faz o Starlette redirecionar GET /metrics
        # (sem barra final) para GET /metrics/ com 307 -- o proprio scrape do
        # Prometheus segue esse redirect. Sem o rstrip, a requisicao pos-
        # redirect chega com path "/metrics/" e escapa da exclusao, poluindo
        # http_requests_total com o proprio trafego de monitoramento (o
        # problema que esta exclusao existe para evitar, ver ADR-0004).
        if path.rstrip("/") in EXCLUDED_PATHS:
            return await call_next(request)

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            # Excecao nao tratada vira 500 no ServerErrorMiddleware, que fica
            # acima deste middleware. Sem este except, erros de servidor nunca
            # apareceriam no painel de taxa de erro.
            REQUEST_LATENCY.labels(request.method, path).observe(
                time.perf_counter() - start
            )
            REQUESTS_TOTAL.labels(request.method, path, "500").inc()
            raise

        REQUEST_LATENCY.labels(request.method, path).observe(
            time.perf_counter() - start
        )
        REQUESTS_TOTAL.labels(request.method, path, str(response.status_code)).inc()
        return response

    app.mount("/metrics", make_asgi_app())
