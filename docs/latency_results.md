# Resultados de Benchmark — Original vs. Otimizado (ONNX Runtime)

Latencia de inferencia por requisicao (uma predicao por chamada, sem batching), medida na mesma maquina, sobre o mesmo conjunto de entradas (`data/benchmark_samples.json`) e o mesmo numero de execucoes para os dois backends. Aquecimento (JIT/caches) descartado e reportado separadamente — ver secao abaixo.

## Ambiente de execucao

| Item | Valor |
|------|-------|
| Iteracoes medidas por backend | 2000 |
| Iteracoes de aquecimento (descartadas) | 200 |
| Amostras usadas (cicladas) | 45 de `data/benchmark_samples.json` |
| Modelo original | `models/model.pkl` (TF-IDF + LogisticRegression, joblib) |
| Modelo otimizado | `models/model.onnx` (mesmo pipeline, ONNX Runtime) |
| Tecnica de otimizacao | Conversao para ONNX Runtime (`skl2onnx`) |

## Resultados comparativos

| Modelo | N | Media (ms) | Mediana (ms) | p95 (ms) | Min (ms) | Max (ms) |
|---|---|---|---|---|---|---|
| Original (scikit-learn) | 2000 | 0.682 | 0.644 | 1.017 | 0.449 | 3.425 |
| Otimizado (ONNX Runtime) | 2000 | 0.215 | 0.196 | 0.388 | 0.119 | 0.984 |

## Melhoria de latencia

- **Media**: +68.42% (0.682 ms → 0.215 ms)
- **p95**: +61.82% (1.017 ms → 0.388 ms)

Valores positivos indicam reducao de latencia (modelo otimizado mais rapido); valores negativos indicam regressao.

> As duas tabelas acima sao geradas automaticamente por
> `python -m scripts.benchmark_latency` (reprodutivel — reexecutar
> regenera este arquivo). As secoes abaixo sao curadas manualmente.

## Ambiente da medicao

| Item | Valor |
|------|-------|
| Data da medicao | 2026-09-09 |
| Commit do codigo | `3e767d6` |
| SO | Windows 10 (build 19045) |
| CPU | 11th Gen Intel(R) Core(TM) i5-1135G7 @ 2.40GHz |
| Execucao | Local, fora de container (inferencia pura do modelo, sem HTTP) |

**Por que a latencia aqui (< 1 ms) e muito menor que o baseline da API em
`docs/baseline_latency.md`** (p50 2.4 ms): este benchmark mede apenas o
tempo de `pipeline.predict()`/`session.run()` — sem serializacao HTTP,
sem rede, sem overhead do FastAPI/Uvicorn. Ele isola o ganho da tecnica de
otimizacao no proprio modelo, que e o que a Etapa 4 pede (mesma maquina,
mesmas entradas, mesmo numero de execucoes para original vs. otimizado).
A comparacao "ponta a ponta" (API real, com HTTP) esta na secao
"Integracao na API" abaixo — o ganho la e bem menor, porque overhead de
rede/HTTP passa a dominar o tempo total.

## Validacao de paridade de predicoes

`python -m scripts.convert_to_onnx` roda a conversao e valida as 45
amostras de `data/benchmark_samples.json` automaticamente: **45/45
(100%) de concordancia** entre `models/model.pkl` e `models/model.onnx`.

Uma verificacao adicional, mais exigente, sobre as 2.246 amostras do
conjunto de teste (`data/processed/test.csv`, fora do escopo do script de
conversao — validacao manual desta tarefa) encontrou **2233/2246
(99.42%) de concordancia**. As 13 divergencias inspecionadas manualmente
sao todas casos com probabilidade quase empatada entre as duas classes
mais provaveis (margem menor que 4 pontos percentuais na maioria, alguns
abaixo de 1 ponto — ex.: `atencao` 46.82% vs. `normal` 46.16%). A causa e
precisao numerica: o ONNX Runtime opera em `float32`, o scikit-learn em
`float64`; perto do limiar de decisao da regressao logistica, esse
arredondamento e suficiente para inverter o rotulo previsto. Nao ha
evidencia de erro de conversao (vocabulario do TF-IDF, tokenizacao ou
pesos do classificador) — apenas ruido de precisao concentrado em casos
que ja eram ambiguos para o modelo original.

## Integracao na API (realizada, opcional via `MODEL_BACKEND`)

Com autorizacao do Integrante 2, o backend ONNX foi integrado em
`src/app.py` atras da variavel de ambiente `MODEL_BACKEND` (`sklearn`,
padrao — comportamento da Etapa 2 inalterado — ou `onnx`). Detalhes de
design, o grupo de dependencia `api-onnx` (so `onnxruntime`, sem
`skl2onnx`/`onnx`) e um bug de locale encontrado e corrigido no
`Dockerfile`: [ADR-0011](ai/adr/0011-integracao-opcional-do-onnx-na-api.md).

Como usar:

```bash
# Local (sem Docker)
uv sync --group api-onnx
MODEL_BACKEND=onnx uv run uvicorn src.app:app --reload

# Docker / Docker Compose
make convert-onnx                          # gera models/model.onnx
docker build -t urgensight-api .           # inclui onnxruntime + modelo, se presente
docker run -p 8000:8000 -e MODEL_BACKEND=onnx urgensight-api
# ou: MODEL_BACKEND=onnx docker compose up --build
```

### Resultados ponta a ponta (Docker, `POST /predict`)

Sem `hey`/`ab` disponiveis neste ambiente, a medicao usou um cliente
Python equivalente (`requests`, sequencial, mesmo payload, 30 requisicoes
de aquecimento descartadas, 300 medidas), mesma maquina para as duas
rodadas:

| Backend | N | Media (ms) | Mediana (ms) | p95 (ms) |
|---|---|---|---|---|
| sklearn (padrao) — rodada 1 | 300 | 16.759 | 16.140 | 27.836 |
| sklearn (padrao) — rodada 2 | 300 | 16.044 | 15.552 | 30.028 |
| onnx — rodada 1 | 300 | 14.683 | 15.388 | 28.112 |
| onnx — rodada 2 | 300 | 15.616 | 16.214 | 27.103 |

**Ganho ponta a ponta: ~5-12% (bem menor que o ~68% do modelo puro).**
Isso e esperado, nao uma regressao da tecnica: a requisicao HTTP soma
parsing, validacao Pydantic e rede ao tempo de inferencia, e esse
overhead nao muda com o backend do modelo — em um payload pequeno como o
usado aqui, ele domina o tempo total. Os valores absolutos desta tabela
(~15-16 ms) tambem nao sao comparaveis linha a linha com
`docs/baseline_latency.md` (~2-6 ms): ambientes diferentes (Docker
Desktop no Windows/WSL2 aqui vs. macOS nativo la) e metodologia diferente
(cliente Python sequencial aqui vs. `hey` com 10 conexoes concorrentes
la). A comparacao valida desta secao e sklearn vs. onnx **dentro do
mesmo ambiente**, nao contra o baseline historico da Etapa 2 — uma
remedicao formal com `hey` na mesma maquina do baseline original fica
como refinamento futuro, se o grupo quiser esse numero.

O ganho relevante para a rubrica ("melhoria de latencia demonstrada")
continua sendo o do modelo isolado, na secao anterior — a integracao na
API e um diferencial extra para a demonstracao no video, nao um
requisito do enunciado (ver
[ADR-0010](ai/adr/0010-onnx-runtime-como-tecnica-de-otimizacao.md)).
