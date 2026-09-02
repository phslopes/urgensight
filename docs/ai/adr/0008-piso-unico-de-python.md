# ADR-0008 — Piso único de Python 3.12

- **Status:** Aceito
- **Data:** 2026-09-02
- **Contexto da decisão:** Etapa 3 (adendo — DVC/uv/Python)

## Contexto

O projeto declarava três pisos diferentes de Python. `pyproject.toml:7` pedia
`>=3.10` e o ruff mirava `py310`; o `Dockerfile` da API e o `ci.yml` usavam
3.12; e `Dockerfile.airflow` fixava `apache/airflow:2.9.3-python3.11`.

O modelo é treinado no container do Airflow e servido pela API. Divergência de
interpretador entre esses dois ambientes é uma das causas clássicas de falha
ao desserializar `models/model.pkl` — a mesma classe de problema que o README
já documenta para `dill` e `scikit-learn`.

Não havia nenhum mecanismo que fizesse essa divergência aparecer: ela só se
manifestaria em runtime.

## Decisão

Piso único `>=3.12` em todo o projeto, incluindo a imagem do Airflow
(`apache/airflow:2.9.3-python3.12` com `constraints-3.12.txt`).

`tests/test_environment_consistency.py` passa a falhar a suíte quando
`pyproject.toml`, `.python-version`, `Dockerfile`, `Dockerfile.airflow` e
`ci.yml` discordam entre si — inclusive quando a URL de constraints deixa de
acompanhar a tag da imagem.

## Alternativas consideradas

**Manter `>=3.10`.** Rejeitada: o piso declarado não descrevia nenhum ambiente
real do projeto, e o README precisava de um aviso de quatro linhas explicando
que o `python3` do sistema podia ser velho demais.

**Manter o Airflow em 3.11 e aceitar a assimetria.** Rejeitada como padrão, mas
mantida como plano B do portão de validação: a tag `2.9.3-python3.12` e o
arquivo `constraints-3.12.txt` foram verificados como existentes antes da
decisão, mas o suporte a 3.12 no Airflow 2.9 é recente.

**Subir o Airflow para 2.10/2.11.** Rejeitada: a DAG já está entregue e vale
15% da nota; trocar a minor do Airflow na reta final da entrega é risco sem
retorno correspondente.

## Consequências

- A imagem do Airflow precisa ser reconstruída (`make dev-airflow --build`).
- `.python-version` passa a ser versionado; quem usa pyenv/uv pega 3.12
  automaticamente.
- `numpy==1.26.4` continua compatível: suporta Python 3.12.
- O teste de coerência precisa ser atualizado de propósito sempre que alguma
  versão mudar — é o ponto, não um efeito colateral.
