# Etapa 3 — Observabilidade e CI/CD — Plano de Implementação

> **Para executores agênticos:** SUB-SKILL OBRIGATÓRIA: use
> `superpowers:subagent-driven-development` (recomendado) ou
> `superpowers:executing-plans` para implementar tarefa a tarefa. Os passos usam
> checkbox (`- [ ]`) para rastreamento.

**Goal:** Entregar a Etapa 3 do Tech Challenge — API instrumentada com Prometheus,
pipeline CI/CD no GitHub Actions, stack de monitoramento em Docker Compose e dashboard
Grafana provisionado, com ADRs e evidências.

**Architecture:** A instrumentação vive em `src/metrics.py`, módulo isolado que expõe
`setup_metrics(app)` e monta `/metrics`; `src/app.py` apenas o registra e atualiza duas
métricas de domínio. O CI usa dummy training sobre um fixture versionado, mantendo o
pipeline hermético (sem rede externa, sem binário no git). O `docker-compose.yml` da raiz
passa a ser a stack de monitoramento; o Airflow migra para arquivo próprio.

**Tech Stack:** Python 3.12, FastAPI, prometheus-client, Docker Compose, Prometheus,
Grafana, GitHub Actions, pytest, ruff.

**Spec:** `docs/ai/specs/2026-09-01-etapa3-observabilidade-cicd-design.md`

## Global Constraints

- Branch de trabalho: `feat/etapa3-observabilidade` (já criada). PR real contra `main`.
- Commits em **Conventional Commits PT-BR** (`feat(api):`, `fix(ci):`, `docs(adr):`).
- Versão do projeto: **`0.3.0`** em `pyproject.toml` e `src/app.py` (hoje divergentes:
  `0.1.0` e `0.2.0`).
- `scikit-learn==1.5.1` fixo — não alterar.
- Classes válidas: `normal`, `atencao`, `urgente`.
- Buckets de latência: `(0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)`.
- Rotas excluídas das métricas de negócio: `/metrics` e `/health`.
- Portas: API `8000`, Prometheus `9090`, Grafana `3000`.
- UID fixo do datasource Grafana: `urgensight-prometheus`.
- `src/train.py` **não deve ser alterado** — já é parametrizável por CLI.
- `.gitignore` **não deve ser alterado** — o modelo continua fora do git.
- Comentários e docstrings em português sem acentos, seguindo o padrão do repositório.
- Rodar `make lint` antes de cada commit.

---

### Task 1: Módulo de métricas HTTP

**Files:**
- Create: `src/metrics.py`
- Create: `tests/test_metrics.py`
- Modify: `requirements.txt`, `pyproject.toml`

**Interfaces:**
- Consumes: nada (primeira tarefa).
- Produces: `src/metrics.py` exportando `REQUESTS_TOTAL` (Counter, labels
  `method`/`path`/`status`), `REQUEST_LATENCY` (Histogram, labels `method`/`path`),
  `MODEL_LOADED` (Gauge, sem labels), `PREDICTIONS_TOTAL` (Counter, label `urgency`),
  `EXCLUDED_PATHS` (frozenset), `LATENCY_BUCKETS` (tuple) e
  `setup_metrics(app: FastAPI) -> None`.

- [ ] **Step 1: Adicionar a dependência**

Em `requirements.txt`, após a linha `uvicorn[standard]>=0.29`:

```
# Instrumentacao de metricas (Etapa 3 - src/metrics.py)
prometheus-client>=0.20
```

Em `pyproject.toml`, dentro de `dependencies`, após `"dill>=0.3.8",`:

```toml
    "prometheus-client>=0.20",
```

Instalar: `uv pip install prometheus-client` (ou `pip install prometheus-client`).

- [ ] **Step 2: Escrever o teste que falha**

Criar `tests/test_metrics.py`:

```python
"""Testes da instrumentacao Prometheus da API (Etapa 3).

As metricas do prometheus_client sao globais por processo e acumulam entre
testes, entao todas as assercoes leem valores por diferenca (antes/depois)
em vez de assumir zero inicial.
"""

from fastapi.testclient import TestClient

from src.app import app
from src.metrics import REQUEST_LATENCY, REQUESTS_TOTAL


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
```

As fixtures `real_model` e `broken_model` hoje vivem em `tests/test_app.py` e precisam
ficar disponíveis também para `tests/test_metrics.py`. Mover para `tests/conftest.py`,
com atenção a uma armadilha: **`mock_pipeline` já existe em `tests/conftest.py:8-15`** e
está duplicada em `tests/test_app.py:22-30`. Colar as três causaria definição duplicada
no mesmo módulo.

Procedimento correto:

1. Em `tests/conftest.py`: apagar a fixture `mock_app_with_model` (não é usada por
   nenhum teste) e colar apenas `real_model` e `broken_model`, copiadas de
   `tests/test_app.py:33-60`. Manter a `mock_pipeline` que já está lá.
2. Em `tests/test_app.py`: apagar as três fixtures (`mock_pipeline`, `real_model`,
   `broken_model`, linhas 22-60) e o import `import pytest`, que deixa de ser usado.
   Manter `from fastapi.testclient import TestClient` e `from src.app import app`.

Verificação: `make test` deve continuar passando os 6 testes de `test_app.py` — se
algum falhar com `fixture not found`, a fixture não foi colada em `conftest.py`.

- [ ] **Step 3: Rodar o teste e confirmar que falha**

Run: `make test`
Expected: FAIL com `ModuleNotFoundError: No module named 'src.metrics'`

- [ ] **Step 4: Implementar `src/metrics.py`**

```python
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
        if path in EXCLUDED_PATHS:
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
```

- [ ] **Step 5: Registrar o middleware em `src/app.py`**

Adicionar ao bloco de imports (após `from pydantic import BaseModel, Field`):

```python
from src.metrics import setup_metrics
```

Imediatamente após o bloco `app = FastAPI(...)` que termina em `src/app.py:125`:

```python
setup_metrics(app)
```

- [ ] **Step 6: Rodar os testes e confirmar que passam**

Run: `make test`
Expected: PASS — os 6 testes existentes de `test_app.py` mais os 4 novos.

Se `test_predict_rejects_unknown_model_output` falhar com exceção propagada em vez
de 500, confirme que `TestClient(app, raise_server_exceptions=False)` continua no teste.

- [ ] **Step 7: Lint e commit**

```bash
make lint
git add src/metrics.py tests/test_metrics.py tests/conftest.py tests/test_app.py requirements.txt pyproject.toml
git commit -m "feat(api): instrumentar API com metricas Prometheus"
```

---

### Task 2: Métricas de domínio e contrato da API

**Files:**
- Modify: `src/app.py` (lifespan, `predict`, versão)
- Modify: `tests/test_metrics.py`
- Modify: `pyproject.toml` (versão), `docs/api_contract.md`

**Interfaces:**
- Consumes: `MODEL_LOADED` e `PREDICTIONS_TOTAL` de `src/metrics.py` (Task 1).
- Produces: `model_loaded` e `predictions_total` populados em runtime; versão `0.3.0`.

- [ ] **Step 1: Escrever os testes que falham**

Acrescentar ao final de `tests/test_metrics.py`:

```python
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
```

Atualizar o import no topo do arquivo para:

```python
from src.metrics import MODEL_LOADED, PREDICTIONS_TOTAL, REQUEST_LATENCY, REQUESTS_TOTAL
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `make test`
Expected: FAIL — `model_loaded` continua em 0.0 e `predictions_total` não incrementa.

- [ ] **Step 3: Atualizar o import em `src/app.py`**

Substituir a linha `from src.metrics import setup_metrics` por:

```python
from src.metrics import MODEL_LOADED, PREDICTIONS_TOTAL, setup_metrics
```

- [ ] **Step 4: Atualizar o lifespan**

Em `src/app.py`, no corpo do `lifespan` (linhas 102-112), o bloco `try/except` passa a:

```python
    global model_pipeline
    try:
        model_pipeline = _load_model(MODEL_PATH)
        MODEL_LOADED.set(1)
        logger.info("Modelo carregado com sucesso: %s", MODEL_PATH)
    except Exception as exc:
        model_pipeline = None
        MODEL_LOADED.set(0)
        logger.error(
            "Falha ao carregar o modelo em %s: %s", MODEL_PATH, exc, exc_info=True
        )
    yield
    model_pipeline = None
    MODEL_LOADED.set(0)
```

- [ ] **Step 5: Instrumentar o endpoint `predict`**

O corpo de `predict` (`src/app.py:175-177`) passa a:

```python
    pipeline = _require_model()
    prediction = pipeline.predict([request.text])[0]
    PREDICTIONS_TOTAL.labels(urgency=str(prediction)).inc()
    return PredictResponse(prediction=PredictionLabel(prediction))
```

- [ ] **Step 6: Alinhar a versão**

`src/app.py:123`: `version="0.2.0",` passa a `version="0.3.0",`
`pyproject.toml:3`: `version = "0.1.0"` passa a `version = "0.3.0"`

- [ ] **Step 7: Rodar os testes**

Run: `make test`
Expected: PASS — 13 testes.

- [ ] **Step 8: Documentar `/metrics` em `docs/api_contract.md`**

Acrescentar uma seção ao documento, no mesmo estilo das seções de `/health` e
`/predict` já existentes:

```markdown
## GET /metrics

Expõe as métricas da aplicação no formato de exposição do Prometheus.

- **Content-Type:** `text/plain; version=0.0.4; charset=utf-8`
- **Corpo:** texto no formato Prometheus, **não** JSON
- **Autenticação:** nenhuma (stack local)

### Métricas expostas

| Métrica | Tipo | Labels | Descrição |
|---|---|---|---|
| `http_requests_total` | Counter | `method`, `path`, `status` | Total de requisições HTTP |
| `http_request_latency_seconds` | Histogram | `method`, `path` | Latência das requisições |
| `model_loaded` | Gauge | — | 1 se o modelo está carregado, 0 caso contrário |
| `predictions_total` | Counter | `urgency` | Predições por classe de urgência |

`GET /metrics` e `GET /health` são deliberadamente excluídos de
`http_requests_total` e `http_request_latency_seconds`: o scrape do Prometheus e o
healthcheck do Docker distorceriam os painéis de tráfego. Ver
`docs/ai/adr/0004-instrumentacao-e-contrato-de-metricas.md`.
```

- [ ] **Step 9: Lint e commit**

```bash
make lint
git add src/app.py tests/test_metrics.py pyproject.toml docs/api_contract.md
git commit -m "feat(api): expor metricas de dominio e documentar /metrics na versao 0.3.0"
```

---

### Task 3: Fixture de dummy training

**Files:**
- Create: `tests/fixtures/sample_dataset.csv`
- Create: `tests/test_sample_fixture.py`

**Interfaces:**
- Consumes: `data/processed/train.csv` (gerado localmente por `make train`).
- Produces: `tests/fixtures/sample_dataset.csv` com colunas `text,target` e as três
  classes representadas — consumido pelo job `smoke-train` da Task 4.

- [ ] **Step 1: Gerar o fixture a partir do corpus real**

Pré-requisito: `data/processed/train.csv` deve existir (rode `make train` se não).

```bash
mkdir -p tests/fixtures
python - <<'PY'
import pandas as pd

df = pd.read_csv("data/processed/train.csv")
sample = (
    df.groupby("target", group_keys=False)
      .apply(lambda g: g.sample(n=20, random_state=42))
      .reset_index(drop=True)
)
sample.to_csv("tests/fixtures/sample_dataset.csv", index=False)
print(sample["target"].value_counts())
print("linhas:", len(sample))
PY
```

Esperado: 60 linhas, 20 por classe.

- [ ] **Step 2: Escrever o teste do fixture**

Criar `tests/test_sample_fixture.py`:

```python
"""Valida o fixture de dummy training usado pelo CI (Etapa 3).

O job smoke-train do GitHub Actions treina um modelo em miniatura sobre este
arquivo. Se ele perder colunas ou classes, o CI quebra de forma obscura --
este teste faz a falha aparecer localmente e com mensagem clara.
"""

from pathlib import Path

import pandas as pd

from src.prepare_dataset import TARGET_COLUMN, TEXT_COLUMN, VALID_TARGETS

FIXTURE_PATH = Path("tests/fixtures/sample_dataset.csv")


def test_fixture_exists():
    assert FIXTURE_PATH.exists(), f"{FIXTURE_PATH} ausente -- ver Task 3 do plano."


def test_fixture_has_required_columns():
    df = pd.read_csv(FIXTURE_PATH)
    assert {TEXT_COLUMN, TARGET_COLUMN} <= set(df.columns)


def test_fixture_covers_all_urgency_classes():
    df = pd.read_csv(FIXTURE_PATH)
    assert set(df[TARGET_COLUMN]) == VALID_TARGETS


def test_fixture_has_no_empty_texts():
    df = pd.read_csv(FIXTURE_PATH)
    assert df[TEXT_COLUMN].str.strip().ne("").all()
```

- [ ] **Step 3: Rodar os testes**

Run: `make test`
Expected: PASS — 17 testes.

- [ ] **Step 4: Validar o dummy training localmente**

Este é exatamente o comando que o CI executará. Rodar antes de confiar nele:

```bash
python -m src.train \
  --train-path tests/fixtures/sample_dataset.csv \
  --test-path tests/fixtures/sample_dataset.csv \
  --model-out /tmp/smoke_model.pkl \
  --metrics-out /tmp/smoke_metrics.md \
  --max-features 500
```

Expected: termina com exit 0 e imprime `Pipeline salvo em /tmp/smoke_model.pkl`.
Acurácia alta é esperada e irrelevante — treino e teste são o mesmo conjunto, o
objetivo é provar que o pipeline roda (MOD3 Aula 3 / MOD5 Aula 6).

- [ ] **Step 5: Commit**

```bash
make lint
git add tests/fixtures/sample_dataset.csv tests/test_sample_fixture.py
git commit -m "test(ci): adicionar fixture de dummy training para o pipeline"
```

---

### Task 4: Workflow do GitHub Actions

**Files:**
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: `tests/fixtures/sample_dataset.csv` (Task 3), `Dockerfile`, `Makefile`.
- Produces: workflow `CI` com os jobs `lint`, `test`, `smoke-train`, `build`.

- [ ] **Step 1: Criar o workflow**

```yaml
name: CI

on:
  push:
    branches: [main, "feat/**"]
  pull_request:
    branches: [main]

env:
  PYTHON_VERSION: "3.12"

jobs:
  lint:
    name: Lint (ruff)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: pip
      - name: Instalar dependencias de lint
        run: pip install -r requirements-dev.txt
      - name: Rodar ruff
        run: ruff check src/ tests/ dags/

  test:
    name: Testes (pytest)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: pip
      - name: Instalar dependencias
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      - name: Rodar pytest
        # Os testes sao mockados e nao dependem de models/model.pkl:
        # tests/test_model_loading.py faz skip automatico quando ausente.
        run: pytest -v

  smoke-train:
    name: Dummy training (pipeline em miniatura)
    runs-on: ubuntu-latest
    needs: [lint, test]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: pip
      - name: Instalar dependencias
        run: pip install -r requirements.txt
      - name: Treinar modelo em amostra minima
        # Fixture versionado: sem download externo, o CI nao depende de
        # terceiros. Prova que src/train.py roda de ponta a ponta.
        run: |
          mkdir -p models
          python -m src.train \
            --train-path tests/fixtures/sample_dataset.csv \
            --test-path tests/fixtures/sample_dataset.csv \
            --model-out models/model.pkl \
            --metrics-out /tmp/smoke_metrics.md \
            --max-features 500
      - name: Publicar artefato para o job de build
        # Jobs rodam em runners isolados, sem filesystem compartilhado.
        uses: actions/upload-artifact@v4
        with:
          name: smoke-model
          path: models/model.pkl
          retention-days: 1

  build:
    name: Build da imagem Docker
    runs-on: ubuntu-latest
    needs: [smoke-train]
    steps:
      - uses: actions/checkout@v4
      - name: Baixar o modelo do job anterior
        uses: actions/download-artifact@v4
        with:
          name: smoke-model
          path: models
      - uses: docker/setup-buildx-action@v3
      - name: Build da imagem (sem push)
        uses: docker/build-push-action@v6
        with:
          context: .
          push: false
          tags: urgensight-api:ci
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

- [ ] **Step 2: Validar a sintaxe YAML localmente**

```bash
python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/ci.yml')); print('YAML valido')"
```

Expected: `YAML valido`

- [ ] **Step 3: Commit e push para disparar o workflow**

```bash
git add .github/workflows/ci.yml
git commit -m "ci(actions): adicionar workflow de lint, testes, dummy training e build"
git push -u origin feat/etapa3-observabilidade
```

- [ ] **Step 4: Verificar o workflow verde**

```bash
gh run watch
```

Expected: os quatro jobs concluem com sucesso. Se `build` falhar em
`COPY models/model.pkl`, confirme que o `download-artifact` gravou em `models/`.

---

### Task 5: Stack de monitoramento no Docker Compose

**Files:**
- Create: `monitoring/prometheus.yml`
- Create: `docker-compose.airflow.yml` (renomeado do atual)
- Modify: `docker-compose.yml` (reescrito), `Makefile`

**Interfaces:**
- Consumes: `Dockerfile`, endpoint `/metrics` (Task 1).
- Produces: serviços `api`, `prometheus` e `grafana`; alvo de scrape `api:8000`;
  targets `make dev`, `make dev-airflow`, `make load`, `make monitoring-down`.

- [ ] **Step 1: Renomear o Compose do Airflow**

```bash
git mv docker-compose.yml docker-compose.airflow.yml
```

- [ ] **Step 2: Criar `monitoring/prometheus.yml`**

```yaml
# Configuracao de scrape do Prometheus (Etapa 3 - UrgenSight).
# O alvo usa o nome do servico do Compose ("api"), resolvido pela rede
# interna -- nao use localhost, que apontaria para o proprio container.
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: urgensight-api
    metrics_path: /metrics
    static_configs:
      - targets: ["api:8000"]
        labels:
          service: urgensight
```

- [ ] **Step 3: Escrever o novo `docker-compose.yml`**

```yaml
# Stack de monitoramento da Etapa 3: API + Prometheus + Grafana.
# A stack do Airflow (Etapa 1.3) vive em docker-compose.airflow.yml.
#
# Pre-requisito: models/model.pkl deve existir. Use `make dev`, que garante
# isso automaticamente, em vez de `docker compose up` direto.
services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
    image: urgensight-api:latest
    ports:
      - "8000:8000"
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:v2.54.1
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    command:
      - --config.file=/etc/prometheus/prometheus.yml
      - --storage.tsdb.path=/prometheus
    depends_on:
      - api
    restart: unless-stopped

  grafana:
    image: grafana/grafana:11.2.0
    ports:
      - "3000:3000"
    environment:
      # Acesso anonimo em modo Viewer: o avaliador abre localhost:3000 e ve
      # o dashboard sem login. admin/admin continua valendo para edicao.
      GF_AUTH_ANONYMOUS_ENABLED: "true"
      GF_AUTH_ANONYMOUS_ORG_ROLE: Viewer
      GF_SECURITY_ADMIN_USER: admin
      GF_SECURITY_ADMIN_PASSWORD: admin
      GF_USERS_DEFAULT_THEME: light
    volumes:
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning:ro
      - ./monitoring/dashboard.json:/var/lib/grafana/dashboards/dashboard.json:ro
    depends_on:
      - prometheus
    restart: unless-stopped

volumes:
  # Preserva a serie temporal entre restarts -- util para nao perder o
  # historico dos graficos durante a gravacao do video.
  prometheus-data:
```

- [ ] **Step 4: Atualizar o `Makefile`**

Substituir o target `dev` e acrescentar os novos. Adicionar `dev-airflow`, `load` e
`monitoring-down` ao `.PHONY` da primeira linha.

```makefile
dev: ensure-model
	docker compose up -d --build
	@echo "API:        http://localhost:8000/docs"
	@echo "Prometheus: http://localhost:9090/targets"
	@echo "Grafana:    http://localhost:3000"

ensure-model:
	@if [ ! -f models/model.pkl ]; then \
		echo "models/model.pkl ausente -- executando make train..."; \
		$(MAKE) train; \
	fi

dev-airflow:
	docker compose -f docker-compose.airflow.yml up -d --build

monitoring-down:
	docker compose down

load:
	$(PYTHON) scripts/generate_load.py
```

Atualizar também o bloco `help` com as novas linhas.

- [ ] **Step 5: Subir a stack e validar**

```bash
make dev
sleep 20
curl -s http://localhost:8000/health
curl -s http://localhost:8000/metrics | head -20
curl -s "http://localhost:9090/api/v1/targets" | grep -o '"health":"[a-z]*"'
```

Expected: `/health` retorna `{"status":"ok","model_loaded":true}`; `/metrics` retorna
texto Prometheus; o target aparece como `"health":"up"`.

- [ ] **Step 6: Commit**

```bash
git add docker-compose.yml docker-compose.airflow.yml monitoring/prometheus.yml Makefile
git commit -m "feat(monitoring): adicionar stack Compose com API, Prometheus e Grafana"
```

---

### Task 6: Dashboard Grafana provisionado

**Files:**
- Create: `monitoring/grafana/provisioning/datasources/prometheus.yml`
- Create: `monitoring/grafana/provisioning/dashboards/dashboards.yml`
- Create: `monitoring/dashboard.json`

**Interfaces:**
- Consumes: métricas da Task 1 e serviço `prometheus` da Task 5.
- Produces: dashboard `UrgenSight — Observabilidade` com 6 painéis, datasource de UID
  `urgensight-prometheus`.

- [ ] **Step 1: Provisionar o datasource**

`monitoring/grafana/provisioning/datasources/prometheus.yml`:

```yaml
# UID fixo e obrigatorio: sem ele o Grafana gera um UID aleatorio e o
# dashboard.json versionado deixa de resolver o datasource em outra maquina.
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    uid: urgensight-prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
```

- [ ] **Step 2: Provisionar o provider de dashboards**

`monitoring/grafana/provisioning/dashboards/dashboards.yml`:

```yaml
apiVersion: 1

providers:
  - name: urgensight
    orgId: 1
    folder: ""
    type: file
    disableDeletion: false
    updateIntervalSeconds: 30
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
      foldersFromFilesStructure: false
```

- [ ] **Step 3: Criar `monitoring/dashboard.json`**

```json
{
  "uid": "urgensight-obs",
  "title": "UrgenSight — Observabilidade",
  "tags": ["urgensight", "etapa3"],
  "timezone": "browser",
  "schemaVersion": 39,
  "version": 1,
  "refresh": "10s",
  "time": { "from": "now-15m", "to": "now" },
  "panels": [
    {
      "id": 1,
      "type": "stat",
      "title": "Total de requisições",
      "gridPos": { "h": 5, "w": 6, "x": 0, "y": 0 },
      "datasource": { "type": "prometheus", "uid": "urgensight-prometheus" },
      "targets": [
        { "expr": "sum(http_requests_total)", "refId": "A", "legendFormat": "total" }
      ]
    },
    {
      "id": 2,
      "type": "stat",
      "title": "Modelo carregado",
      "gridPos": { "h": 5, "w": 6, "x": 6, "y": 0 },
      "datasource": { "type": "prometheus", "uid": "urgensight-prometheus" },
      "fieldConfig": {
        "defaults": {
          "mappings": [
            {
              "type": "value",
              "options": {
                "0": { "text": "INDISPONÍVEL", "color": "red", "index": 0 },
                "1": { "text": "OK", "color": "green", "index": 1 }
              }
            }
          ]
        },
        "overrides": []
      },
      "targets": [
        { "expr": "model_loaded", "refId": "A", "legendFormat": "model_loaded" }
      ]
    },
    {
      "id": 3,
      "type": "timeseries",
      "title": "Throughput (req/s)",
      "gridPos": { "h": 5, "w": 12, "x": 12, "y": 0 },
      "datasource": { "type": "prometheus", "uid": "urgensight-prometheus" },
      "fieldConfig": { "defaults": { "unit": "reqps" }, "overrides": [] },
      "targets": [
        { "expr": "sum(rate(http_requests_total[1m]))", "refId": "A", "legendFormat": "rps" }
      ]
    },
    {
      "id": 4,
      "type": "timeseries",
      "title": "Latência (p50 / p95 / p99)",
      "gridPos": { "h": 8, "w": 12, "x": 0, "y": 5 },
      "datasource": { "type": "prometheus", "uid": "urgensight-prometheus" },
      "fieldConfig": { "defaults": { "unit": "s" }, "overrides": [] },
      "targets": [
        {
          "expr": "histogram_quantile(0.50, sum(rate(http_request_latency_seconds_bucket[5m])) by (le))",
          "refId": "A",
          "legendFormat": "p50"
        },
        {
          "expr": "histogram_quantile(0.95, sum(rate(http_request_latency_seconds_bucket[5m])) by (le))",
          "refId": "B",
          "legendFormat": "p95"
        },
        {
          "expr": "histogram_quantile(0.99, sum(rate(http_request_latency_seconds_bucket[5m])) by (le))",
          "refId": "C",
          "legendFormat": "p99"
        }
      ]
    },
    {
      "id": 5,
      "type": "timeseries",
      "title": "Taxa de erro (não-2xx)",
      "gridPos": { "h": 8, "w": 12, "x": 12, "y": 5 },
      "datasource": { "type": "prometheus", "uid": "urgensight-prometheus" },
      "fieldConfig": { "defaults": { "unit": "percentunit", "min": 0, "max": 1 }, "overrides": [] },
      "targets": [
        {
          "expr": "sum(rate(http_requests_total{status!~\"2..\"}[5m])) / clamp_min(sum(rate(http_requests_total[5m])), 0.0001)",
          "refId": "A",
          "legendFormat": "taxa de erro"
        }
      ]
    },
    {
      "id": 6,
      "type": "timeseries",
      "title": "Predições por classe de urgência",
      "gridPos": { "h": 8, "w": 24, "x": 0, "y": 13 },
      "datasource": { "type": "prometheus", "uid": "urgensight-prometheus" },
      "targets": [
        {
          "expr": "sum(rate(predictions_total[5m])) by (urgency)",
          "refId": "A",
          "legendFormat": "{{urgency}}"
        }
      ]
    }
  ]
}
```

Nota sobre `clamp_min` no painel 5: sem ele, quando não há tráfego o denominador é
zero e o Grafana exibe `NaN` em vez de uma linha em zero.

- [ ] **Step 4: Validar o JSON**

```bash
python -c "import json; d=json.load(open('monitoring/dashboard.json')); print('paineis:', len(d['panels']))"
```

Expected: `paineis: 6`

- [ ] **Step 5: Recriar a stack e conferir o Grafana**

```bash
make monitoring-down && make dev
sleep 25
open http://localhost:3000
```

Expected: o dashboard "UrgenSight — Observabilidade" abre **sem login** e os seis
painéis existem (ainda sem dados — a Task 7 gera o tráfego).

- [ ] **Step 6: Commit**

```bash
git add monitoring/
git commit -m "feat(monitoring): provisionar datasource e dashboard Grafana com 6 paineis"
```

---

### Task 7: Gerador de carga

**Files:**
- Create: `scripts/generate_load.py`

**Interfaces:**
- Consumes: `POST /predict` da API.
- Produces: CLI com `--url`, `--duration`, `--rps`, `--error-rate`.

- [ ] **Step 1: Implementar o script**

```python
"""Gerador de trafego sintetico para popular os paineis do Grafana (Etapa 3).

Envia requisicoes ao endpoint /predict a uma taxa configuravel. Uma fracao
delas usa payload invalido de proposito (--error-rate), porque a API saudavel
tem taxa de erro zero e um painel de erro vazio nao demonstra observabilidade
nenhuma. Este e trafego de teste deliberado, nao simulacao de falha real.

Uso:
    python scripts/generate_load.py --duration 120 --rps 20 --error-rate 0.1
"""

import argparse
import json
import random
import time
from pathlib import Path

import requests

BENCHMARK_PATH = Path("data/benchmark_samples.json")

# Usado quando data/benchmark_samples.json nao existe, para o script nao
# depender do dataset preparado.
FALLBACK_TEXTS = [
    "Paciente apresenta dor toracica intensa e dispneia progressiva.",
    "Exame de rotina sem alteracoes dignas de nota.",
    "Massa abdominal palpavel, necessita investigacao complementar.",
    "Quadro de cefaleia persistente com deficit neurologico focal.",
]


def load_texts() -> list[str]:
    """Carrega textos reais do benchmark; cai para o fallback se ausente."""
    if not BENCHMARK_PATH.exists():
        return FALLBACK_TEXTS
    samples = json.loads(BENCHMARK_PATH.read_text(encoding="utf-8"))
    return [s["text"] for s in samples] or FALLBACK_TEXTS


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:8000/predict")
    parser.add_argument("--duration", type=int, default=120, help="segundos")
    parser.add_argument("--rps", type=float, default=20.0, help="requisicoes por segundo")
    parser.add_argument(
        "--error-rate",
        type=float,
        default=0.1,
        help="fracao de payloads invalidos (0.0 a 1.0)",
    )
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args(argv)


def main(argv=None) -> None:
    args = parse_args(argv)
    random.seed(args.seed)
    texts = load_texts()

    interval = 1.0 / args.rps
    deadline = time.time() + args.duration
    sent = ok = errors = 0

    print(
        f"Gerando carga em {args.url} por {args.duration}s "
        f"({args.rps} req/s, {args.error_rate:.0%} invalidas)..."
    )

    while time.time() < deadline:
        if random.random() < args.error_rate:
            # Payload sem o campo obrigatorio "text" -> 422 do Pydantic.
            payload = {"texto_errado": "campo invalido"}
        else:
            payload = {"text": random.choice(texts)}

        try:
            response = requests.post(args.url, json=payload, timeout=5)
            sent += 1
            if response.status_code == 200:
                ok += 1
            else:
                errors += 1
        except requests.RequestException as exc:
            errors += 1
            print(f"Falha de conexao: {exc}")

        time.sleep(interval)

    print(f"Enviadas: {sent} | 200: {ok} | nao-2xx ou falhas: {errors}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Rodar contra a stack e popular os painéis**

```bash
make dev
python scripts/generate_load.py --duration 180 --rps 20 --error-rate 0.1
```

Expected: ao final imprime o resumo com ~3600 enviadas e ~10% de não-2xx.

- [ ] **Step 3: Conferir os painéis populados**

Abrir `http://localhost:3000`. Expected: throughput ~20 req/s, latência p95 na casa
de poucos milissegundos, taxa de erro ~0,10, predições distribuídas entre as classes.

Se o painel de latência aparecer vazio, confira que os buckets de `LATENCY_BUCKETS`
foram aplicados — buckets errados produzem `histogram_quantile` sem resultado útil.

- [ ] **Step 4: Commit**

```bash
make lint
git add scripts/generate_load.py
git commit -m "feat(monitoring): adicionar gerador de carga para popular os paineis"
```

---

### Task 8: Architecture Decision Records

**Files:**
- Create: `docs/ai/adr/0001-mapeamento-proxy-do-dataset.md`
- Create: `docs/ai/adr/0002-estrategia-de-nuvem-e-modo-de-servico.md`
- Create: `docs/ai/adr/0003-artefato-de-modelo-no-ci.md`
- Create: `docs/ai/adr/0004-instrumentacao-e-contrato-de-metricas.md`
- Create: `docs/ai/adr/0005-stack-de-monitoramento-como-codigo.md`
- Create: `docs/ai/adr/README.md`

**Interfaces:**
- Consumes: `docs/dataset.md`, `README.md` (seção de arquitetura), spec da Etapa 3.
- Produces: cinco ADRs referenciados por `src/metrics.py` e `docs/api_contract.md`.

- [ ] **Step 1: Criar o índice**

`docs/ai/adr/README.md`:

```markdown
# Architecture Decision Records

Registros das decisões arquiteturais do UrgenSight, no formato
[MADR](https://adr.github.io/madr/). Cada arquivo documenta uma decisão, as
alternativas consideradas e as consequências aceitas.

| ADR | Título | Status |
|---|---|---|
| [0001](0001-mapeamento-proxy-do-dataset.md) | Mapeamento proxy do dataset para classes de urgência | Aceito |
| [0002](0002-estrategia-de-nuvem-e-modo-de-servico.md) | Estratégia de nuvem e modo de serviço | Aceito |
| [0003](0003-artefato-de-modelo-no-ci.md) | Artefato de modelo no CI via dummy training | Aceito |
| [0004](0004-instrumentacao-e-contrato-de-metricas.md) | Instrumentação e contrato de métricas | Aceito |
| [0005](0005-stack-de-monitoramento-como-codigo.md) | Stack de monitoramento como código | Aceito |
```

- [ ] **Step 2: Escrever ADR-0003 (o modelo desta tarefa)**

Todos os ADRs seguem esta estrutura. `docs/ai/adr/0003-artefato-de-modelo-no-ci.md`:

```markdown
# ADR-0003 — Artefato de modelo no CI via dummy training

- **Status:** Aceito
- **Data:** 2026-09-01
- **Contexto da decisão:** Etapa 3 (CI/CD)

## Contexto

`Dockerfile:24` executa `COPY models/model.pkl`, mas `.gitignore` exclui
`models/*.pkl` e `data/raw/*`. Em um clone limpo não existe nem o modelo nem os
dados para gerá-lo, então o build da imagem falha no GitHub Actions e no Docker
Compose.

Três consumidores precisam do artefato: o job de build do CI, a stack de
monitoramento e o avaliador que clona o repositório. Os testes unitários **não**
precisam — são mockados, e `tests/test_model_loading.py` faz skip automático.

## Decisão

O CI gera um modelo descartável via **dummy training** sobre
`tests/fixtures/sample_dataset.csv` (60 amostras versionadas, 20 por classe), e o
transporta ao job de build com `actions/upload-artifact`.

O Compose e o avaliador usam o **modelo real**: `make dev` verifica a existência de
`models/model.pkl` e executa `make train` automaticamente quando ausente.

## Alternativas consideradas

**Treinar o modelo completo no CI.** Rejeitada: `src/prepare_dataset.py` baixa o
corpus de `raw.githubusercontent.com`, o que acopla o CI a um repositório de
terceiros. Uma mudança de branch ou indisponibilidade daquele host deixaria o CI
vermelho sem nenhuma alteração no nosso código — e CI verde é evidência avaliada.

**Versionar `models/model.pkl` (1,2 MB).** Rejeitada: torna o CI determinístico, mas
o binário pode dessincronizar silenciosamente de `src/train.py`, e contraria tanto a
narrativa de artefato regenerável quanto a orientação do curso (MOD5, DVC/MLflow) de
não versionar modelos em Git.

**Treinar dentro do Dockerfile.** Rejeitada: build sempre lento, dependente de rede e
não determinístico.

## Consequências

- O CI é hermético: sem rede externa e sem binário no repositório.
- O job `smoke-train` prova que `src/train.py` roda de ponta a ponta, cumprindo o
  papel de "pipeline em miniatura" descrito em MOD3 Aula 1 e MOD5 Aula 6.
- O job `build` valida que **a imagem monta**, não que o modelo é bom; a qualidade do
  modelo continua sendo aferida por `tests/test_model_loading.py` contra o modelo real.
- O fixture precisa ser regenerado se o esquema de `data/processed/train.csv` mudar;
  `tests/test_sample_fixture.py` faz essa falha aparecer localmente.
```

- [ ] **Step 3: Escrever os quatro ADRs restantes**

Mesma estrutura de seções (Contexto / Decisão / Alternativas consideradas /
Consequências), extraindo o conteúdo das fontes indicadas:

| ADR | Fonte do conteúdo | Alternativas a registrar |
|---|---|---|
| 0001 | `docs/dataset.md`, seções "Mapeamento para as classes do projeto" e "Limitação conhecida" | rótulos sintéticos; outro dataset com urgência real; Protocolo de Manchester |
| 0002 | `README.md`, seção de arquitetura da Etapa 2.4 | batch vs. real-time; as outras duas nuvens entre AWS/Azure/GCP |
| 0004 | Spec §4.1 | `prometheus-fastapi-instrumentator`; buckets padrão das aulas; incluir `/metrics` e `/health` nas métricas |
| 0005 | Spec §6.1 e §6.2 | Compose em `monitoring/`; profiles em arquivo único; dashboard montado na UI e exportado |

O ADR-0001 deve preservar a ressalva já escrita em `docs/dataset.md`: o mapeamento é
didático e não constitui triagem clínica real.

- [ ] **Step 4: Commit**

```bash
git add docs/ai/adr/
git commit -m "docs(adr): registrar as cinco decisoes arquiteturais do projeto"
```

---

### Task 9: Evidências, README e tracking

**Files:**
- Create: `docs/monitoring_evidence.md`
- Create: `docs/evidence/` (prints)
- Modify: `README.md`, `docs/specs/phase-tracking.md`

**Interfaces:**
- Consumes: stack rodando (Task 5-7), workflow verde (Task 4).
- Produces: entregáveis documentais da Etapa 3.

- [ ] **Step 1: Coletar as evidências**

Com `make dev` no ar e após rodar `make load`, capturar em `docs/evidence/`:

| Arquivo | Conteúdo |
|---|---|
| `prometheus_targets.png` | `http://localhost:9090/targets` com a API **UP** |
| `grafana_dashboard.png` | dashboard com os 6 painéis populados |
| `github_actions_push.png` | workflow verde no push |
| `github_actions_pr.png` | workflow verde no pull request |

E a saída bruta das métricas:

```bash
mkdir -p docs/evidence
curl -s http://localhost:8000/metrics > docs/evidence/metrics_output.txt
```

- [ ] **Step 2: Escrever `docs/monitoring_evidence.md`**

Documento com uma seção por evidência, cada uma registrando: o que demonstra, o
comando que a reproduz, a data da captura e o SHA do commit correspondente
(`git rev-parse --short HEAD`). Incluir os quatro prints e o trecho relevante de
`metrics_output.txt` mostrando as quatro métricas.

- [ ] **Step 3: Atualizar o README**

Acrescentar, sem alterar as seções das Etapas 1 e 2:

1. Badge no topo:
   `[![CI](https://github.com/Edwardmaster7/urgensight/actions/workflows/ci.yml/badge.svg)](https://github.com/Edwardmaster7/urgensight/actions/workflows/ci.yml)`
2. Seção **Testes e Lint**: `make test`, `make test-cov`, `make lint`.
3. Seção **CI/CD**: os quatro jobs, os gatilhos e a explicação do dummy training.
4. Seção **Monitoramento**: `make dev`, as três URLs, os painéis, `make load` e
   `make monitoring-down`. Deixar explícito que o Airflow agora sobe com
   `make dev-airflow`.

- [ ] **Step 4: Atualizar `docs/specs/phase-tracking.md`**

Marcar como concluídos os itens 3.1 a 3.5 e os entregáveis da Etapa 3; alterar o
status da Etapa 3 na tabela do topo para ✅; atualizar as linhas de 06/09 e 10/09 no
cronograma e a seção de pendências prioritárias.

- [ ] **Step 5: Verificação final**

```bash
make lint && make test
```

Expected: PASS, sem findings de lint.

Percorrer a lista de critérios de aceite da §10 da spec e confirmar cada item.

- [ ] **Step 6: Commit e abertura do PR**

```bash
git add docs/ README.md
git commit -m "docs(etapa3): consolidar evidencias, README e tracking da Etapa 3"
git push
gh pr create --title "feat: Etapa 3 — observabilidade e CI/CD" --body-file - <<'PRBODY'
## Resumo

Entrega a Etapa 3 do Tech Challenge: API instrumentada com Prometheus, pipeline
CI/CD no GitHub Actions, stack de monitoramento em Docker Compose e dashboard
Grafana provisionado.

## Mudanças

- `src/metrics.py`: 4 métricas com buckets calibrados ao baseline medido
- `.github/workflows/ci.yml`: lint ∥ test → smoke-train → build
- `docker-compose.yml`: stack de monitoring (Airflow migrou para arquivo próprio)
- `monitoring/`: Prometheus, datasource e dashboard com 6 painéis
- `scripts/generate_load.py`: gerador de tráfego
- `docs/ai/adr/`: 5 ADRs, incluindo 2 retroativos das Etapas 1 e 2

## Design

`docs/ai/specs/2026-09-01-etapa3-observabilidade-cicd-design.md`

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01YKVjCgrkafbyHzVN2gLmBp
PRBODY
```
