# Etapa 3 — Observabilidade e CI/CD — Documento de Design

> **Data:** 2026-09-01
> **Etapa:** 3 (`phase-tracking.md`) — Testes, CI/CD e Observabilidade
> **Responsável:** Eduardo Batista
> **Critérios atendidos:** CI/CD (15%) + Monitoramento (20%)
> **Status:** aprovado em brainstorming; pendente de plano de implementação

---

## 1. Contexto

O Tech Challenge da Fase 3 exige uma stack local de observabilidade (API + Prometheus +
Grafana via Docker Compose) e um pipeline CI/CD no GitHub Actions com pelo menos duas
automações. Este documento fecha o design dos dois blocos.

### 1.1. Divergência de numeração entre o PDF e o plano do grupo

O PDF oficial (`docs/specs/MLET - Tech Challenge Fase 3.pdf`) organiza as etapas por
disciplina e coloca **CI/CD na Etapa 2**; a Etapa 3 oficial é só monitoramento. O
`docs/specs/phase-tracking.md` organiza por integrante e agrupa **testes + CI/CD +
observabilidade** na Etapa 3.

A Etapa 2 do grupo está marcada como concluída sem que nenhum workflow exista. Manter a
leitura do PDF deixaria o CI/CD órfão entre uma etapa encerrada e outra que não o
reivindica — 15% da nota sem responsável. **Este design adota o escopo do
`phase-tracking.md`.**

### 1.2. Estado verificado do repositório

Levantado por inspeção direta do código, não pelo tracking:

| Bloco                  | Estado  | Evidência                                                                      |
| ---------------------- | ------- | ------------------------------------------------------------------------------- |
| 3.1 Testes + lint      | Pronto  | 6 testes de API em`tests/test_app.py`, ruff em `pyproject.toml`             |
| 3.2 GitHub Actions     | Ausente | `.github/` não existe                                                        |
| 3.3 Prometheus         | Ausente | `prometheus-client` não está em `requirements.txt` nem `pyproject.toml` |
| 3.4 Compose monitoring | Ausente | `docker-compose.yml` da raiz é exclusivo do Airflow                          |
| 3.5 Grafana            | Ausente | `monitoring/` e `scripts/` não existem                                     |

### 1.3. Restrições descobertas

1. **Artefato de modelo indisponível em clone limpo.** `Dockerfile:24` faz
   `COPY models/model.pkl`, mas `.gitignore:23` exclui `models/*.pkl` e `.gitignore:17`
   exclui `data/raw/*`. O build da imagem falha no CI e no Compose.
2. **Buckets de latência descalibrados.** O baseline real em
   `docs/baseline_latency.md` é p50 2,4 ms / p95 5,8 ms / p99 21,2 ms. Os buckets
   padrão das aulas (`0.01` em diante) colocam praticamente todas as amostras no
   primeiro bucket e inutilizam `histogram_quantile`.
3. **Um único worker Uvicorn.** `Dockerfile:37` não passa `--workers`, então
   `prometheus_client` opera em processo único e **não** precisa de multiprocess mode.
4. **Versões divergentes.** `src/app.py:123` declara `0.2.0`; `pyproject.toml:3`
   declara `0.1.0`. O hook `.claude/scripts/verify-semver.sh` apenas avisa (`exit 0`).
5. **`src/app.py` sem camada transversal.** Confirmado via knowledge graph: o módulo
   contém schemas, lifespan e rotas diretamente, sem middleware ou router. Os únicos
   importadores externos são `tests/conftest.py` e `tests/test_app.py`.

### 1.4. Fundamentação nas disciplinas da fase

O material do curso define os padrões canônicos adotados aqui:

- **MOD6 Aula 2** — hands-on de Prometheus: `prometheus_client`, `prometheus.yml` com
  `scrape_config`, Compose, verificação de targets e PromQL.
- **MOD3 Aula 7 (Eng. de Software)** — padrão `metrics.py` com `setup_metrics(app)`,
  middleware HTTP e `app.mount("/metrics", make_asgi_app())`; alerta explícito para
  "buckets calibrados à sua SLO".
- **MOD4 Aula 7 (APIs)** — métricas de domínio de ML: `model_loaded` como `Gauge`,
  `http_request_latency_seconds` como `Histogram` rotulado.
- **MOD3 CI/CD Aulas 1, 2 e 5** — dummy training sobre amostra mínima no PR, build
  imutável em todo PR, `actions/cache` e cache de camadas Docker.
- **MOD3 Aula 3 (Eng. de Software)** e **MOD5 Aula 6** — pipeline em miniatura no CI:
  treinar em amostra reduzida "só para verificar se a pipeline roda sem erros".

---

## 2. Decisões

| #   | Decisão                 | Escolha                                                        | Motivo                                                         |
| --- | ------------------------ | -------------------------------------------------------------- | -------------------------------------------------------------- |
| Q1  | Escopo                   | Inclui CI/CD                                                   | Evita órfão entre Etapa 2 encerrada e Etapa 3                |
| Q2  | Artefato de modelo no CI | **Dummy training** sobre fixture versionado              | Hermético: sem rede externa e sem binário no git → ADR-0003 |
| Q3  | Instrumentação         | `prometheus_client` puro em `src/metrics.py`               | Exigido pelo PDF; padrão MOD3 A7 → ADR-0004                  |
| Q4  | Compose                  | Raiz vira monitoring; Airflow →`docker-compose.airflow.yml` | Avaliador procura`docker-compose.yml` na raiz → ADR-0005    |
| Q5  | Grafana                  | Provisionado por arquivo + JSON versionado                     | Sobe pronto, sem cliques → ADR-0005                           |
| Q6  | Fluxo                    | Branch`feat/etapa3-observabilidade` + PR real                | Única forma de exercitar o gatilho`pull_request`            |
| Q7  | ADRs retroativos         | Incluir os das Etapas 1 e 2                                    | Raciocínio já escrito; cobrem pontos avaliados               |
| Q8  | Fixture do dummy         | `tests/fixtures/sample_dataset.csv` próprio                 | Desacopla do`benchmark_samples.json` da Etapa 4              |
| Q9  | Modelo do Compose        | Real, com Makefile garantindo o pré-requisito                 | Dashboard de 20% não pode exibir modelo de brinquedo          |
| Q10 | Buckets                  | `[0.001 … 1.0]`                                             | Calibrados ao baseline medido                                  |
| Q11 | Métricas                | 4 (ver §4.1)                                                  | Cobrem os 3 painéis obrigatórios + domínio                  |
| Q12 | Taxa de erro             | Painel mede não-2xx; carga injeta erros                       | Painel vazio não demonstra observabilidade                    |
| Q13 | Jobs                     | `lint` ∥ `test` → `smoke-train` → `build`           | Feedback rápido; build só após tudo passar                  |
| Q14 | Versão                  | `0.3.0` em ambos os arquivos                                 | `/metrics` é endpoint novo retrocompatível (MINOR)         |
| Q15 | Acesso                   | Grafana anônimo Viewer; volume só no Prometheus              | Reduz fricção do avaliador; preserva série na gravação    |
| Q16 | Exclusões               | `/metrics` e `/health` fora das métricas de negócio      | Scrape 15s + healthcheck 30s poluiriam os painéis             |
| Q17 | ADRs                     | Cinco, em`docs/ai/adr/`                                      | Ver §8                                                        |

---

## 3. Arquitetura

### 3.1. Componentes e fronteiras

```
┌─────────────────────── docker-compose.yml (raiz) ───────────────────────┐
│                                                                          │
│  ┌────────────────┐      scrape 15s     ┌──────────────┐                 │
│  │  api           │ ◄──────────────────  │  prometheus  │                │
│  │  :8000         │   GET /metrics       │  :9090       │                │
│  │                │                      │  vol: tsdb   │                │
│  │  src/app.py    │                      └──────┬───────┘                │
│  │  + metrics.py  │                             │ datasource (uid fixo)  │
│  └────────────────┘                      ┌──────▼───────┐                │
│                                          │  grafana     │                │
│                                          │  :3000       │                │
│                                          │  provisioned │                │
│                                          └──────────────┘                │
└──────────────────────────────────────────────────────────────────────────┘
        ▲
        │ POST /predict (tráfego sintético, com --error-rate)
   scripts/generate_load.py
```

`src/metrics.py` é um módulo isolado: define as métricas, expõe `setup_metrics(app)` e
monta `/metrics`. `src/app.py` apenas o registra e chama dois pontos de atualização
(`MODEL_LOADED` no lifespan, `PREDICTIONS_TOTAL` no `predict`). Assim `app.py` não
absorve a preocupação transversal, e as métricas ficam testáveis isoladamente.

### 3.2. Estrutura de arquivos

```
.github/workflows/ci.yml                          [novo]
monitoring/prometheus.yml                         [novo]
monitoring/dashboard.json                         [novo]
monitoring/grafana/provisioning/datasources/prometheus.yml   [novo]
monitoring/grafana/provisioning/dashboards/dashboards.yml    [novo]
scripts/generate_load.py                          [novo]
src/metrics.py                                    [novo]
tests/fixtures/sample_dataset.csv                 [novo]
tests/test_metrics.py                             [novo]
docs/ai/adr/000{1..5}-*.md                        [novo]
docs/monitoring_evidence.md                       [novo]
docker-compose.yml                                [reescrito: monitoring]
docker-compose.airflow.yml                        [renomeado do atual]
src/app.py                                        [+ setup_metrics, 2 pontos, versão]
requirements.txt / pyproject.toml                 [+ prometheus-client, versão 0.3.0]
Makefile                                          [+ targets, dev → airflow]
README.md                                         [+ seções, badge]
docs/api_contract.md                              [+ /metrics]
.gitignore                                        [inalterado]
```

`src/train.py` **não é alterado**: já aceita `--train-path`, `--test-path`,
`--model-out`, `--metrics-out` e `--max-features` por CLI, que é tudo que o dummy
training precisa.

---

## 4. Instrumentação (bloco 3.3)

### 4.1. Contrato de métricas

| Métrica                         | Tipo      | Labels                           | Origem              |
| -------------------------------- | --------- | -------------------------------- | ------------------- |
| `http_requests_total`          | Counter   | `method`, `path`, `status` | MOD3 A7             |
| `http_request_latency_seconds` | Histogram | `method`, `path`             | MOD4 A7             |
| `model_loaded`                 | Gauge     | —                               | MOD4 A7             |
| `predictions_total`            | Counter   | `urgency`                      | domínio do projeto |

**Buckets** de `http_request_latency_seconds`:
`[0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]`.

Justificativa: com p50 = 2,4 ms e p95 = 5,8 ms, os três primeiros buckets concentram a
massa da distribuição e dão resolução real ao `histogram_quantile`, enquanto a cauda até
1 s captura o p99 (21,2 ms) e degradações futuras.

**Exclusões.** `/metrics` e `/health` não alimentam `http_requests_total` nem
`http_request_latency_seconds`. Sem isso, o scrape de 15 s injetaria 240 req/h e o
healthcheck do Docker (30 s) mais 120 req/h — os painéis de total e de throughput
passariam a medir majoritariamente o próprio monitoramento.

**Cardinalidade.** A API expõe apenas `/health` e `/predict`, sem path parameters, então
o label `path` é seguro. Rotas com parâmetros no futuro exigirão template de rota.

### 4.2. Ciclo de vida

- `lifespan` sucesso → `MODEL_LOADED.set(1)`; falha → `MODEL_LOADED.set(0)`.
- `predict` bem-sucedido → `PREDICTIONS_TOTAL.labels(urgency=<classe>).inc()`.
- `/metrics` responde em `text/plain; version=0.0.4` (formato de exposição Prometheus),
  não JSON.

---

## 5. CI/CD (bloco 3.2)

### 5.1. Grafo de jobs

```
        ┌────────┐
        │  lint  │──┐
        └────────┘  │   ┌─────────────┐   ┌────────┐
                    ├──►│ smoke-train │──►│ build  │
        ┌────────┐  │   └─────────────┘   └────────┘
        │  test  │──┘
        └────────┘
```

Gatilhos: `push` e `pull_request` na `main`. Isso satisfaz o mínimo de duas automações
obrigatórias (lint e testes) com folga.

| Job             | Comando                                                                                                                                                                                                  | Observação                                                                        |
| --------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| `lint`        | `ruff check src/ tests/ dags/`                                                                                                                                                                         | `actions/cache` para pip                                                          |
| `test`        | `pytest`                                                                                                                                                                                               | Não depende de modelo: os testes são mockados e`test_model_loading.py` faz skip |
| `smoke-train` | `python -m src.train --train-path tests/fixtures/sample_dataset.csv --test-path tests/fixtures/sample_dataset.csv --model-out models/model.pkl --metrics-out /tmp/smoke_metrics.md --max-features 500` | Pipeline em miniatura (MOD5 A6)                                                     |
| `build`       | `docker/build-push-action` com cache de camadas, sem push                                                                                                                                              | Build imutável do PR (MOD3 CI/CD A2)                                               |

**Transporte do artefato entre jobs.** Jobs do GitHub Actions rodam em runners
isolados, sem filesystem compartilhado: o `models/model.pkl` produzido pelo
`smoke-train` não existe no runner do `build`. O artefato é passado explicitamente com
`actions/upload-artifact` ao final do `smoke-train` e `actions/download-artifact` no
início do `build`, antes do `docker build`.

Alternativa descartada: colapsar o treino em um step do próprio job `build`. Seria mais
simples, mas perde o sinal separado — com jobs distintos, uma falha de `src/train.py`
aparece como `smoke-train` vermelho, e não como um build quebrado de causa ambígua.

### 5.2. Por que dummy training

O fixture `tests/fixtures/sample_dataset.csv` (~60 linhas, 20 por classe, extraídas do
corpus real) é versionado. Consequências:

- **Sem rede externa.** Não há download de `raw.githubusercontent.com` — o CI não fica
  vermelho porque um repositório de terceiros mudou de branch.
- **Sem binário no git.** O `.gitignore` permanece intacto e a narrativa de artefato
  regenerável se mantém.
- **Prova o pipeline de treino.** O job falha se `src/train.py` quebrar, que é
  exatamente o propósito descrito em MOD3 Aula 1.

O modelo gerado é descartável e serve apenas para o `COPY` do Dockerfile: o job `build`
valida que **a imagem monta**, não que o modelo é bom. Qualidade do modelo é aferida
por `tests/test_model_loading.py` localmente, contra o modelo real.

### 5.3. Versionamento

`0.3.0` em `pyproject.toml` e `src/app.py` (MINOR: endpoint novo retrocompatível). A
divergência atual 0.1.0/0.2.0 é corrigida no mesmo commit. `docs/api_contract.md` ganha
a seção de `/metrics`.

---

## 6. Stack de monitoramento (blocos 3.4 e 3.5)

### 6.1. Compose

O `docker-compose.yml` da raiz passa a definir `api`, `prometheus` e `grafana`; a stack
do Airflow migra para `docker-compose.airflow.yml`. O avaliador que abre o repositório e
roda `docker compose up` encontra exatamente o que a rubrica descreve.

- **Portas:** API 8000, Prometheus 9090, Grafana 3000.
- **Volumes:** volume nomeado para o TSDB do Prometheus (preserva a série entre
  restarts durante a gravação do vídeo). Grafana sem volume — tudo é provisionado.
- **Grafana:** acesso anônimo com papel `Viewer` habilitado; `admin/admin` continua
  disponível para edição.
- **Prometheus:** `scrape_interval: 15s`, target `api:8000` via rede do Compose.

`Makefile`: `make dev` passa a subir a stack de monitoring e **garante o pré-requisito**
— se `models/model.pkl` não existir, roda `make train` antes. O Airflow ganha um target
próprio. Isso remove a fricção de o avaliador precisar conhecer a ordem dos comandos.

### 6.2. Dashboard

Provisionado por arquivo, com UID de datasource fixo (`urgensight-prometheus`) — sem UID
fixo, um JSON exportado da UI referencia um UID gerado e não reimporta em outra máquina.

| # | Painel                 | Consulta                                                                                   |
| - | ---------------------- | ------------------------------------------------------------------------------------------ |
| 1 | Total de requisições | `sum(http_requests_total)`                                                               |
| 2 | Throughput (RPS)       | `sum(rate(http_requests_total[1m]))`                                                     |
| 3 | Latência p50/p95/p99  | `histogram_quantile(0.95, sum(rate(http_request_latency_seconds_bucket[5m])) by (le))`   |
| 4 | Taxa de erro           | `sum(rate(http_requests_total{status!~"2.."}[5m])) / sum(rate(http_requests_total[5m]))` |
| 5 | Predições por classe | `sum(rate(predictions_total[5m])) by (urgency)`                                          |
| 6 | Modelo carregado       | `model_loaded`                                                                           |

Mínimo obrigatório são três painéis (1, 3 e 4); os demais são o diferencial de domínio.

O JSON é mantido em `monitoring/dashboard.json`, servindo simultaneamente como fonte do
provisionamento e como o entregável "JSON do dashboard" exigido pelo PDF.

### 6.3. Geração de carga

`scripts/generate_load.py` com `--duration`, `--rps` e `--error-rate` (default 0.1).
A fração de erro envia payloads inválidos, produzindo respostas 422.

Isso existe porque a API saudável tem taxa de erro zero, e um painel de taxa de erro
vazio não demonstra observabilidade alguma. Os erros são **tráfego de teste deliberado
e documentado**, não simulação de falha real. Note que os erros naturais do sistema são
422 (validação Pydantic) e 503 (modelo ausente), e não 500 — por isso o painel mede
não-2xx em vez do `status=~"5.."` clássico das aulas.

---

## 7. Testes

Novos testes em `tests/test_metrics.py`, sem rede e sem modelo real:

1. `/metrics` responde 200 no formato de exposição Prometheus.
2. `http_requests_total` incrementa após uma chamada a `/predict`.
3. `http_request_latency_seconds` registra observação com os labels esperados.
4. `predictions_total` incrementa no label da classe prevista.
5. `model_loaded` vale 1 com modelo carregado e 0 no cenário `broken_model`.
6. Requisições a `/metrics` e `/health` **não** aparecem em `http_requests_total`.

O teste 6 é o que protege a decisão Q16 contra regressão silenciosa.

As fixtures existentes (`real_model`, `broken_model`) são reaproveitadas. Como as
métricas do `prometheus_client` são globais por processo, os testes devem ler valores
por diferença (antes/depois) em vez de assumir zero inicial.

---

## 8. ADRs

Em `docs/ai/adr/`, PT-BR, formato MADR (Contexto / Decisão / Alternativas consideradas /
Consequências / Status):

| ADR  | Assunto                                                                       |
| ---- | ----------------------------------------------------------------------------- |
| 0001 | Mapeamento proxy do dataset: 5 categorias clínicas → 3 classes de urgência |
| 0002 | Estratégia de nuvem e batch vs. real-time                                    |
| 0003 | Artefato de modelo no CI via dummy training                                   |
| 0004 | Instrumentação e contrato de métricas (nomes, buckets, exclusões)         |
| 0005 | Stack de monitoramento como código                                           |

Os dois primeiros são retroativos: as decisões foram tomadas nas Etapas 1 e 2 e estão
hoje apenas como texto corrido em `docs/dataset.md` e no README. São também as duas
mais passíveis de questionamento na avaliação e no vídeo.

---

## 9. Evidências

`docs/monitoring_evidence.md` consolida, com a data e o SHA do commit de cada captura:

- Print do Prometheus em `Status > Targets` com a API como **UP**
- Print do dashboard populado após execução do `generate_load.py`
- Print do workflow verde no GitHub Actions (push e pull request)
- Saída bruta de `GET /metrics`
- Link do PR com o CI verde

README recebe: badge do GitHub Actions, seção de execução da stack, seção de CI/CD e
comandos de lint e teste.

---

## 10. Critérios de aceite

- [ ] `make lint` e `make test` verdes localmente, incluindo os novos testes
- [ ] Workflow verde em push **e** em pull request reais
- [ ] `GET /metrics` responde em formato Prometheus com as 4 métricas
- [ ] `/metrics` e `/health` ausentes de `http_requests_total`
- [ ] `docker compose up --build` sobe API, Prometheus e Grafana
- [ ] Target da API aparece **UP** no Prometheus
- [ ] Grafana abre em `localhost:3000` sem login e exibe o dashboard provisionado
- [ ] Mínimo de 3 painéis populados com dados reais de `generate_load.py`
- [ ] `monitoring/dashboard.json` versionado
- [ ] Cinco ADRs escritos
- [ ] `docs/monitoring_evidence.md` com todos os prints
- [ ] README atualizado com badge e instruções
- [ ] Versão `0.3.0` consistente e `docs/api_contract.md` com `/metrics`
- [ ] `phase-tracking.md` atualizado com o estado real

---

## 11. Fora de escopo

- Alertas do Prometheus / Alertmanager (não exigidos)
- Push da imagem para registry (o PDF pede build, não publicação)
- Métricas de drift do modelo
- `node_exporter` ou `cAdvisor` (o requisito é a API, não a infraestrutura)
- Multiprocess mode do `prometheus_client` (só necessário com múltiplos workers)
- Qualquer item da Etapa 4 (conversão ONNX, benchmark comparativo)
