# Baseline de Latência — API UrgenSight

Registro da latência baseline da API de inferência rodando em container
Docker, medida com o [`hey`](https://github.com/rakyll/hey) (ferramenta de
load testing HTTP). Serve como referência para comparar regressões de
performance em iterações futuras (ex: troca de modelo, adição de
middlewares, conversão ONNX).

## Ambiente de execução

Preencher antes da medição:

| Item | Valor |
|------|-------|
| Data da medição | 2026-08-30 |
| Commit do código | `3600445` |
| Versão da imagem | `urgensight:latest` |
| Docker version | 29.4.1 |
| SO da máquina host | macOS 26.6.2 (Darwin 25.6.0) |
| CPU | Apple M4 Pro |
| RAM disponível | 24 GB |
| Workers do Uvicorn | 1 (padrão do CMD) |
| Modelo | `models/model.pkl` (TF-IDF + LogisticRegression) |

## Cenário de teste

Endpoint alvo: `POST /predict` (inferência real do pipeline TF-IDF + LR).

Payload fixo usado em todas as requisições (representativo de um laudo real):

```json
{"text": "Paciente apresenta tosse e febre. Necessita triagem urgente."}
```

Parâmetros do `hey`:

- **Requisições totais**: `-n 100`
- **Concorrência**: `-c 4`
- **Método**: `POST`

## Procedimento

### 1. Subir a API em container

```bash
docker build -t urgensight-api .
docker run -d -p 8000:8000 --name urgensight-api urgensight-api
```

Aguardar o health check ficar `healthy`:

```bash
docker inspect --format='{{.State.Health.Status}}' urgensight-api
# deve retornar: healthy
```

### 2. Aquecer o servidor (descartar)

As primeiras requisições incluem JIT/warm-up do Python e do scikit-learn.
Executar 100 requisições de aquecimento **antes** da medição oficial:

```bash
hey -n 100 -c 10 \
  -m POST \
  -H "Content-Type: application/json" \
  -d '{"text": "Severe chest pain with dyspnea and diaphoresis, ECG shows ST elevation, suspect acute myocardial infarction."}' \
  http://localhost:8000/predict > nul 2>&1
```

> **Nota Windows**: `> nul 2>&1` descarta a saída. Em Linux/macOS use
> `> /dev/null 2>&1`.

### 3. Medir a latência baseline

```bash
hey -n 1000 -c 10 \
  -m POST \
  -H "Content-Type: application/json" \
  -d '{"text": "Severe chest pain with dyspnea and diaphoresis, ECG shows ST elevation, suspect acute myocardial infarction."}' \
  http://localhost:8000/predict
```

O `hey` imprime um resumo com tempos médio, p95, p99 e histograma de
latência. Copiar os valores relevantes para a tabela abaixo.

Alternativa com Apache Bench (`ab`), caso `hey` não esteja disponível —
criar antes um arquivo `payload.json` com o JSON acima:

```bash
ab -n 1000 -c 10 \
  -T "application/json" \
  -p payload.json \
  http://localhost:8000/predict
```

### 4. Registrar os resultados

| Métrica | Resultado | Observações |
|---------|-----------|-------------|
| Requisições totais | 100 | — |
| Requisições com erro | 0 | 100% de respostas HTTP 200 |
| **Tempo mínimo** | 0.9 ms | Fastest |
| **Tempo médio** | 3.2 ms | Latência média total (rede + processamento) |
| **p50 (mediana)** | 2.4 ms | 50% das requisições abaixo deste valor |
| **p75** | 3.1 ms | 75% das requisições abaixo deste valor |
| **p90** | 4.0 ms | 90% das requisições abaixo deste valor |
| **p95** | 5.8 ms | 95% das requisições abaixo deste valor |
| **p99** | 21.2 ms | 99% das requisições abaixo deste valor |
| **Tempo máximo** | 21.2 ms | Slowest |
| Requisições/segundo | 1220.31 req/s | Throughput do servidor |

### 5. Encerrar

```bash
docker stop urgensight-api && docker rm urgensight-api
```

## Interpretação rápida

- **Latência esperada**: TF-IDF + Logistic Regression sobre texto curto é
  CPU-bound e muito rápido; p99 < 50 ms é razoável em hardware moderno.
- **p99 alto vs média**: indica contenção (GC, thread pool do Uvicorn,
  swap de memória). Verificar `docker stats` durante o teste.
- **Erros > 0**: a API pode estar throttled ou o container sem memória.
  Não registrar baseline com erros — investigar a causa primeiro.
