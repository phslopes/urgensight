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
| Data da medição | _AAAA-MM-DD_ |
| Commit do código | _hash (ex: `a1b2c3d`)_ |
| Versão da imagem | _ex: `urgensight-api:a1b2c3d`_ |
| Docker version | _ex: 29.7.2_ |
| SO da máquina host | _ex: Windows 11 / Ubuntu 24.04 / WSL2_ |
| CPU | _ex: Intel i7-12700H (14C/20T)_ |
| RAM disponível | _ex: 16 GB_ |
| Workers do Uvicorn | _1 (padrão do CMD)_ |
| Modelo | `models/model.pkl` (TF-IDF + LogisticRegression) |

## Cenário de teste

Endpoint alvo: `POST /predict` (inferência real do pipeline TF-IDF + LR).

Payload fixo usado em todas as requisições (representativo de um laudo real,
~200 caracteres):

```json
{"text": "Severe chest pain with dyspnea and diaphoresis, ECG shows ST elevation, suspect acute myocardial infarction."}
```

Parâmetros do `hey`:

- **Requisições totais**: `-n 1000`
- **Concorrência**: `-c 10`
- **Timeout por requisição**: `-t 10` (10s)

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
| Requisições totais | 1000 | — |
| Requisições com erro | _ex: 0_ | Deve ser 0; caso contrário, investigar antes de registrar |
| **Tempo médio** | _ex: 8.2 ms_ | Latência média total (rede + processamento) |
| **p50 (mediana)** | _ex: 7.5 ms_ | 50% das requisições abaixo deste valor |
| **p95** | _ex: 14.1 ms_ | 95% das requisições abaixo deste valor |
| **p99** | _ex: 22.8 ms_ | 99% das requisições abaixo deste valor |
| **Tempo máximo** | _ex: 45.3 ms_ | Outlier observado |
| Requisições/segundo | _ex: 1200 req/s_ | Throughput do servidor |

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
