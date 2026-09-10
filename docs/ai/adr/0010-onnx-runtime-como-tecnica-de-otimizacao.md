# ADR-0010 — ONNX Runtime como técnica de otimização de latência

- **Status:** Aceito
- **Data:** 2026-09-09
- **Contexto da decisão:** Etapa 4 (Otimização e Benchmark de Latência) — `feat/etapa-4-otimizacao-latencia`

## Contexto

A Etapa 4 exige aplicar pelo menos uma técnica de otimização de latência
vista em aula (ONNX Runtime, quantização básica ou pruning) sobre o
modelo treinado na Etapa 1 (`models/model.pkl`: `TfidfVectorizer` +
`LogisticRegression`, ver [ADR-0001](0001-mapeamento-proxy-do-dataset.md))
e demonstrar ganho de latência de forma reprodutível, na mesma máquina,
com o mesmo conjunto de entradas e o mesmo número de execuções para o
modelo original e o otimizado.

`docs/model_metrics.md` já registrava, desde a Etapa 1, uma nota do
Integrante 1 para o Integrante 4: o pipeline usa `TfidfVectorizer` +
`LogisticRegression`/`LinearSVC`, ambos suportados pelo conversor
[`sklearn-onnx`](https://github.com/onnx/sklearn-onnx), com conversão
preliminar esperada sem obstáculos.

## Decisão

Adotar **conversão para ONNX Runtime** (via `skl2onnx`) como técnica de
otimização, conforme já sinalizado pela Etapa 1:

1. `scripts/convert_to_onnx.py` converte `models/model.pkl` para
   `models/model.onnx` usando `skl2onnx.to_onnx`, com `StringTensorType`
   como input (o pipeline recebe texto cru, a vetorização TF-IDF também é
   convertida) e `zipmap=False` (saída de probabilidades como tensor
   denso, não lista de dicts).
2. `models/model.onnx` **não é commitado no git** — mesmo tratamento hoje
   dado a `models/model.pkl` (`.gitignore`, regenerável localmente). A
   conversão é determinística a partir de um `model.pkl` fixo, então
   versionar o artefato binário adicionaria peso ao repositório sem
   ganho de reprodutibilidade.
3. `scripts/benchmark_latency.py` mede a latência de inferência por
   requisição (uma predição por chamada, sem batching) dos dois backends
   sobre `data/benchmark_samples.json`, com uma rodada de aquecimento
   descartada e reportada separadamente, e grava o resultado em
   `docs/latency_results.md`.
4. **Escopo de integração:** esta branch não altera `src/app.py`. A
   integração do modelo ONNX na API é responsabilidade da Etapa 2
   (Integrante 2); `docs/latency_results.md` documenta os passos
   sugeridos, conforme o handoff previsto no checklist da Etapa 4
   (4.2: "Entregar instruções de integração do modelo otimizado ao
   Integrante 2").

## Pin de versão do `onnx`

`skl2onnx`/`onnxruntime` trazem `onnx` como dependência transitiva. A
versão mais recente disponível no momento (`onnx==1.19.0`) referencia em
runtime o dtype `ml_dtypes.float4_e2m1fn`, que só existe em
`ml-dtypes>=0.5.0` — e `ml-dtypes>=0.5.0` exige `numpy>=2.1.0`. O projeto
fixa `numpy==1.26.4` como piso obrigatório em todo o ambiente
([ADR-0007](0007-uv-com-lock-unico.md)), porque o pipeline serializado em
`models/model.pkl` precisa ser desserializável de forma idêntica entre o
treino (Airflow) e a inferência (API) — subir o numpy quebraria essa
garantia para todo o projeto, não só para a Etapa 4.

Em vez de alterar o piso de `numpy` (fora do escopo desta etapa e
arriscado para as Etapas 1–3 já fechadas), o grupo opcional
`optimization` fixa `onnx<1.18` (resolvido para `onnx==1.17.0`), a última
faixa compatível com `ml-dtypes==0.4.1`. Validado localmente: conversão e
inferência funcionam sem erro nessa combinação.

```toml
[dependency-groups]
optimization = [
    "onnxruntime>=1.29.0",
    "skl2onnx>=1.20.0",
    "onnx<1.18",
]
```

Este grupo é **opcional** e separado do grupo `dev`/`pipeline` — não
entra na imagem da API por padrão nem no `uv sync --frozen` usado pelos
jobs de lint/teste do CI, para não inflar o ambiente padrão de quem não
está trabalhando na otimização. Quem for integrar o ONNX na API
(Integrante 2) precisa instalá-lo explicitamente
(`uv sync --group optimization`).

## Validação de paridade e divergências encontradas

`scripts/convert_to_onnx.py` valida automaticamente as predições do
modelo ONNX contra o pipeline original sobre as 45 amostras de
`data/benchmark_samples.json`: **100% de concordância**.

Uma verificação manual adicional (fora do escopo do script, feita para
esta ADR) sobre as 2.246 amostras do conjunto de teste
(`data/processed/test.csv`) encontrou **99.42% de concordância** (13
divergências). Todas as 13 são casos em que as duas classes mais
prováveis do modelo original têm probabilidades quase empatadas (margem
tipicamente abaixo de 4 pontos percentuais, algumas abaixo de 1 ponto).
A causa é precisão numérica — ONNX Runtime opera em `float32`, o
scikit-learn em `float64` — e não um erro de conversão do vocabulário
TF-IDF ou dos pesos do classificador. Detalhes em
`docs/latency_results.md`.

## Alternativas consideradas

**Quantização básica (plano B sinalizado pela Etapa 1).** Não foi
necessária: a conversão ONNX funcionou de primeira, sem incompatibilidade
de tipo de modelo (o risco citado pelo checklist do projeto — conversão
ONNX de pipelines TF-IDF + RandomForest — não se aplica aqui, pois o
modelo escolhido na Etapa 1 já foi `LogisticRegression`, compatível).
Fica como direção futura caso o modelo baseline mude para um estimador
não suportado pelo `sklearn-onnx`.

**Pruning.** Não avaliado: pruning se aplica a modelos com estrutura
esparsificável (árvores, redes neurais); `LogisticRegression` sobre
vetores TF-IDF não tem um caminho direto e padronizado de pruning nas
bibliotecas usadas no curso. ONNX Runtime já entregava o ganho esperado
sem essa complexidade adicional.

**Integrar o modelo ONNX diretamente em `src/app.py` nesta mesma
branch.** Rejeitada por delimitação de responsabilidade entre etapas: o
arquivo é de propriedade da Etapa 2, e uma mudança de backend de
inferência na API viva merece revisão de quem mantém aquele contrato.
Em vez disso, os passos de integração ficam documentados em
`docs/latency_results.md` como handoff.

## Consequências

- `models/model.onnx` precisa ser regenerado localmente
  (`make convert-onnx` ou `python -m scripts.convert_to_onnx`) sempre que
  `models/model.pkl` for retreinado — não há passo automático que
  garanta os dois artefatos sincronizados fora do fluxo manual descrito
  no README.
- O grupo `optimization` acopla o projeto a uma faixa específica de
  `onnx` (`<1.18`) enquanto `numpy` permanecer em `1.26.4`. Se
  [ADR-0007](0007-uv-com-lock-unico.md) for revisado para subir o piso de
  `numpy`, este pin pode ser relaxado — revisar junto.
- A comparação "ponta a ponta" (API completa, com HTTP, em Docker) contra
  o baseline de `docs/baseline_latency.md` não foi executada nesta
  branch — o benchmark aqui mede apenas o backend de inferência, isolando
  o ganho da técnica de otimização em si. Fica como próximo passo para
  quem integrar o ONNX na API.
