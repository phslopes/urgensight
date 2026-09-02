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

> **Atualização (2026-09-02, [ADR-0007](0007-uv-com-lock-unico.md)):** o job
> `smoke-train` passou a instalar dependências com `uv sync --frozen
> --no-default-groups --group pipeline` em vez de `pip install -r
> requirements.txt`. Como `pandas`, `numpy` e `scikit-learn` já estão em
> `[project.dependencies]` (ver ADR-0007), esse `--group pipeline` hoje só
> acrescenta `dvc`, que o `smoke-train` nem usa — pequena ineficiência aceita.
> A decisão registrada aqui — dummy training sobre fixture versionado, sem
> rede — permanece em vigor.
