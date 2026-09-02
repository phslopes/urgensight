# Evidências de Monitoramento e CI/CD — Etapa 3

> **Data da coleta:** 2026-09-01
> **SHA do commit correspondente:** `d739c2a` (branch `feat/etapa3-observabilidade`)

Este documento registra, para cada evidência exigida pela Etapa 3, o que ela
demonstra, o comando exato que a reproduz e onde o artefato bruto está salvo em
`docs/evidence/`.

**Nota sobre o formato das evidências:** as evidências abaixo foram coletadas via
linha de comando (`curl`, `gh`) em vez de capturas de tela (`.png`), porque são
texto/JSON verificável e reproduzível por qualquer pessoa que rode os mesmos
comandos — diferente de uma imagem, que não pode ser conferida por quem lê o
repositório. Capturas de tela do dashboard Grafana e da execução do GitHub
Actions podem ser adicionadas manualmente pelo usuário em `docs/evidence/` caso
deseje complementar com material visual para o vídeo STAR; as evidências abaixo
são a fonte de verdade verificável via linha de comando.

---

## 1. Target da API UP no Prometheus

**O que demonstra:** com a stack de monitoramento no ar (`make dev`), o
Prometheus descobre e faz scrape do endpoint `/metrics` da API com sucesso
(`"health": "up"`), confirmando que o serviço `prometheus` está corretamente
configurado para coletar métricas do serviço `api` pela rede interna do Compose.

**Comando que reproduz:**

```bash
make dev
# aguardar o container da API ficar healthy:
docker inspect --format='{{.State.Health.Status}}' $(docker compose ps -q api)
curl -s http://localhost:9090/api/v1/targets | python3 -m json.tool
```

**Artefato:** [`docs/evidence/prometheus_targets.json`](evidence/prometheus_targets.json)

Trecho relevante:

```json
{
  "labels": { "instance": "api:8000", "job": "urgensight-api", "service": "urgensight" },
  "scrapeUrl": "http://api:8000/metrics",
  "health": "up",
  "lastError": ""
}
```

---

## 2. Métricas reais expostas em `GET /metrics`

**O que demonstra:** as quatro métricas definidas em `src/metrics.py`
(`http_requests_total`, `http_request_latency_seconds`, `model_loaded`,
`predictions_total`) aparecem no formato de exposição do Prometheus, com valores
populados por tráfego real gerado por `scripts/generate_load.py`.

**Comando que reproduz:**

```bash
make dev
python scripts/generate_load.py --duration 20 --rps 10 --error-rate 0.1
curl -sL http://localhost:8000/metrics
```

**Artefato:** [`docs/evidence/metrics_output.txt`](evidence/metrics_output.txt)

Trecho relevante (após gerar 177 requisições, 158 com sucesso e 19 com payload
inválido de propósito):

```
http_requests_total{method="POST",path="/predict",status="200"} 158.0
http_requests_total{method="POST",path="/predict",status="422"} 19.0
model_loaded 1.0
predictions_total{urgency="atencao"} 51.0
predictions_total{urgency="normal"} 46.0
predictions_total{urgency="urgente"} 61.0
```

O histograma `http_request_latency_seconds` também está presente no arquivo
completo, com buckets calibrados ao baseline real (`docs/baseline_latency.md`).

**Achado durante a coleta desta evidência:** a primeira coleta (antes do commit
`d739c2a`) mostrou `http_requests_total{method="GET",path="/metrics/",status="200"}`
poluindo o contador — o `Mount("/metrics", ...)` do Starlette redireciona
`GET /metrics` (sem barra final) para `GET /metrics/` com `307`, e a requisição
pós-redirect (inclusive o próprio scrape do Prometheus, que segue redirects)
chegava ao middleware com o path `/metrics/`, que não batia com o
`EXCLUDED_PATHS = {"/metrics", "/health"}` original. Isso contrariava
diretamente a decisão registrada na
[ADR-0004](ai/adr/0004-instrumentacao-e-contrato-de-metricas.md) de manter
`/metrics` e `/health` fora de `http_requests_total`. Corrigido em
`src/metrics.py` normalizando a barra final antes da checagem de exclusão
(`path.rstrip("/") in EXCLUDED_PATHS`); a evidência acima já reflete o
comportamento corrigido, confirmado por `tests/test_metrics.py` (7 testes
verdes) e pela ausência de qualquer entrada `path="/metrics*"` ou
`path="/health*"` no arquivo de evidência.

---

## 3. Workflow do GitHub Actions verde

**O que demonstra:** o pipeline de CI/CD (`.github/workflows/ci.yml`), com os
quatro jobs `lint → test → smoke-train → build`, executa com sucesso na branch
`feat/etapa3-observabilidade`.

**Comando que reproduz:**

```bash
gh run list --branch feat/etapa3-observabilidade --limit 5 \
  --json databaseId,name,status,conclusion,event
```

**Artefato:** [`docs/evidence/github_actions_runs.json`](evidence/github_actions_runs.json)

O run mais recente no momento da coleta:
[`33574292784`](https://github.com/Edwardmaster7/urgensight/actions/runs/33574292784)
(evento `push`, `conclusion: success`).

---

## 4. Jobs individuais do workflow

**O que demonstra:** os quatro jobs do pipeline (`Lint (ruff)`, `Testes
(pytest)`, `Dummy training (pipeline em miniatura)`, `Build da imagem Docker`)
concluem individualmente com sucesso, confirmando as duas automações
obrigatórias (lint e testes) mais o treino simulado e o build da imagem.

**Comando que reproduz:**

```bash
gh run view 33574292784 --json jobs -q '.jobs[] | {name, conclusion}'
```

**Artefato:** [`docs/evidence/github_actions_jobs.txt`](evidence/github_actions_jobs.txt)

```
{"conclusion":"success","name":"Testes (pytest)"}
{"conclusion":"success","name":"Lint (ruff)"}
{"conclusion":"success","name":"Dummy training (pipeline em miniatura)"}
{"conclusion":"success","name":"Build da imagem Docker"}
```

---

## 5. Dashboard Grafana provisionado

**O que demonstra:** `monitoring/dashboard.json` está versionado no
repositório com 6 painéis (acima do mínimo de 3 exigido), provisionados
automaticamente ao subir o Grafana — sem necessidade de configuração manual.

**Comando que reproduz:**

```bash
python3 -c "
import json
d = json.load(open('monitoring/dashboard.json'))
for p in d['panels']:
    print('-', p['title'])
"
```

Saída:

```
- Total de requisições
- Modelo carregado
- Throughput (req/s)
- Latência (p50 / p95 / p99)
- Taxa de erro (não-2xx)
- Predições por classe de urgência
```

Acesse `http://localhost:3000` (sem login, acesso anônimo em modo Viewer) após
`make dev` e `make load` para ver os painéis populados com dados reais.
