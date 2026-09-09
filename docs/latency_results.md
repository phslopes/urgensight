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
A comparacao "ponta a ponta" com o baseline da API exige integrar o
modelo ONNX na API e rodar `hey` de novo — ver instrucoes abaixo.

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

## Instrucoes de integracao para o Integrante 2 (API)

Este pacote de otimizacao **nao altera `src/app.py`** — a integracao na
API e responsabilidade da Etapa 2. Passos sugeridos para plugar o modelo
ONNX no lugar do `joblib`/scikit-learn:

1. Adicionar o grupo opcional `optimization` ao ambiente da API:
   `uv sync --group optimization` (traz `onnxruntime` + `skl2onnx`; ver
   `pyproject.toml`).
2. Gerar o artefato antes do build da imagem (mesmo tratamento de
   `models/model.pkl` — nao e commitado no git, ver `.gitignore`):
   `python -m scripts.convert_to_onnx`.
3. No lifespan da API, carregar uma `onnxruntime.InferenceSession` sobre
   `models/model.onnx` em vez de (ou alem de, atras de uma flag) chamar
   `load_pipeline`.
4. Na inferencia, montar o input como
   `numpy.array([[texto]], dtype=object)` e chamar
   `session.run(None, {input_name: onnx_input})`; o output `"label"` ja
   vem como string (`normal`/`atencao`/`urgente`), pronto para
   `PredictionLabel(...)`.
5. Incluir `models/model.onnx` no `Dockerfile` (mesmo passo que hoje copia
   `models/model.pkl`) e reexecutar o baseline de latencia com `hey`
   (mesmo procedimento de `docs/baseline_latency.md`) para obter o numero
   comparavel ponta a ponta — o ganho medido aqui (~60-70% no modelo puro)
   tende a ser proporcionalmente menor no tempo total da requisicao, pois
   parte da latencia da API (parsing HTTP, validacao Pydantic, rede) nao
   muda com a troca de backend do modelo.

Caso a equipe opte por nao integrar ONNX na API antes da entrega, esta
secao serve como evidencia documentada da tecnica aplicada e do ganho
demonstrado no nivel do modelo, que e o entregavel exigido pela rubrica
da Etapa 4 ("melhoria de latencia demonstrada").
