# ADR-0004 — Instrumentação e contrato de métricas

- **Status:** Aceito
- **Data:** 2026-09-01
- **Contexto da decisão:** Etapa 3 (Observabilidade)

## Contexto

A Etapa 3 exige instrumentar a API UrgenSight com métricas Prometheus, cobrindo
tanto o padrão genérico de observabilidade de uma API HTTP (das aulas do módulo)
quanto o domínio específico do projeto (classificação de urgência). Isso implica
decidir quais métricas expor, com quais labels, quais buckets de latência usar no
histograma, e quais rotas devem — ou não — alimentar essas métricas.

Duas restrições concretas vieram do próprio ambiente do projeto: (1) o baseline de
latência real já medido (`docs/baseline_latency.md`) mostra p50 = 2,4 ms, p95 = 5,8
ms e p99 = 21,2 ms — uma ordem de grandeza abaixo dos buckets padrão ensinados em
aula, que começam em 0.01 s; e (2) a própria infraestrutura de observabilidade gera
tráfego HTTP contínuo contra a API (scrape do Prometheus a cada 15 s, healthcheck
do Docker a cada 30 s), que não é tráfego de negócio.

## Decisão

O contrato de métricas, implementado em `src/metrics.py`, define:

| Métrica | Tipo | Labels | Origem |
|---|---|---|---|
| `http_requests_total` | Counter | `method`, `path`, `status` | MOD3 A7 |
| `http_request_latency_seconds` | Histogram | `method`, `path` | MOD4 A7 |
| `model_loaded` | Gauge | — | MOD4 A7 |
| `predictions_total` | Counter | `urgency` | domínio do projeto |

**Buckets** de `http_request_latency_seconds`: `[0.001, 0.0025, 0.005, 0.01, 0.025,
0.05, 0.1, 0.25, 0.5, 1.0]`, calibrados ao baseline real (p50 2,4 ms, p95 5,8 ms):
os três primeiros buckets concentram a massa da distribuição e dão resolução real
ao `histogram_quantile`, enquanto a cauda até 1 s captura o p99 (21,2 ms) e
degradações futuras.

**Exclusões:** `/metrics` e `/health` **não** alimentam `http_requests_total` nem
`http_request_latency_seconds`. Sem essa exclusão, o scrape de 15 s injetaria ~240
req/h e o healthcheck do Docker (30 s) mais ~120 req/h, e os painéis de total e de
throughput passariam a medir majoritariamente o próprio monitoramento em vez do
tráfego de inferência real.

**Cardinalidade:** a API expõe apenas `/health` e `/predict`, sem path parameters,
então o label `path` é seguro (não gera séries ilimitadas). Rotas com parâmetros no
futuro exigirão template de rota antes de entrar no label.

**Ciclo de vida:** `lifespan` bem-sucedido define `MODEL_LOADED.set(1)`; falha
define `MODEL_LOADED.set(0)`. Uma predição bem-sucedida incrementa
`PREDICTIONS_TOTAL.labels(urgency=<classe>)`. `/metrics` responde em
`text/plain; version=0.0.4` (formato de exposição do Prometheus), não JSON.

A implementação vive isolada em `src/metrics.py`: `src/app.py` apenas registra
`setup_metrics(app)` e atualiza as métricas de domínio nos pontos relevantes, sem
absorver essa preocupação transversal no módulo da API.

## Alternativas consideradas

**Usar `prometheus-fastapi-instrumentator` em vez de `prometheus_client` puro.**
Rejeitada: a biblioteca automatiza o padrão genérico de métricas HTTP (contagem e
latência por rota), mas o projeto precisa de duas métricas de domínio
(`model_loaded` e `predictions_total`) que não fazem parte do escopo dela, além da
exclusão explícita de `/metrics` e `/health` e dos buckets calibrados ao baseline —
customizações que exigiriam contornar a automação da biblioteca de qualquer forma.
Implementar diretamente com `prometheus_client` mantém o contrato de métricas
totalmente explícito e sob controle do projeto, sem uma camada de abstração extra
sobre um instrumentador com convenções próprias.

**Usar os buckets padrão das aulas (a partir de 0.01 s).** Rejeitada: com p50 = 2,4
ms e p95 = 5,8 ms medidos no baseline real, praticamente toda a massa da
distribuição cairia no primeiro bucket (0.01 s), tornando `histogram_quantile`
incapaz de diferenciar p50 de p95 — o histograma existiria, mas seria inútil para
os painéis de latência do dashboard.

**Incluir `/metrics` e `/health` nas métricas de negócio.** Rejeitada: o tráfego
gerado pela própria infraestrutura de observabilidade (scrape do Prometheus e
healthcheck do Docker) passaria a dominar os contadores de total de requisições e
throughput, mascarando o volume real de tráfego de inferência (`/predict`) que os
painéis pretendem mostrar.

## Consequências

- Os painéis de latência (p50/p95/p99) do dashboard Grafana refletem fielmente a
  distribuição real da API, porque os buckets foram calibrados a ela.
- Os painéis de total de requisições, throughput e taxa de erro medem apenas
  tráfego de negócio (`/predict`), não ruído de infraestrutura — condição para que
  a geração de carga sintética (`scripts/generate_load.py`) produza sinais
  interpretáveis nesses painéis.
- Se o baseline de latência mudar significativamente (ex.: modelo mais pesado, nova
  dependência de I/O), os buckets em `src/metrics.py` precisam ser revisados — eles
  não são um padrão neutro, são específicos a este baseline.
- Novas rotas com path parameters não podem simplesmente herdar o label `path`
  atual sem antes aplicar um template de rota, sob risco de explosão de
  cardinalidade no Prometheus.
