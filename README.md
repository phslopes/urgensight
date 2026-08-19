# UrgenSight

Sistema de triagem automática de exames de texto (laudos médicos) para
classificação de urgência em 3 classes: `normal`, `atencao`, `urgente`.
Projeto acadêmico (Tech Challenge — FIAP MLET).

## Status

- [x] Etapa 1.1 — Dataset e preparação
- [ ] Etapa 1.2 — Modelo baseline
- [ ] Etapa 1.3 — DAG Airflow

## Estrutura do projeto

```
data/
  raw/            # CSVs originais baixados (não versionado)
  processed/      # train.csv / test.csv gerados (não versionado)
  benchmark_samples.json  # amostras fixas para teste/benchmark (versionado)
src/
  prepare_dataset.py      # download, limpeza, mapeamento e split do dataset
tests/
  test_prepare_dataset.py # testes automatizados (pytest)
models/           # modelos treinados serializados (não versionado)
docs/
  dataset.md               # fonte, formato e mapeamento de classes
  dataset_distribution.md  # relatório gerado automaticamente
dags/             # DAGs do Airflow
```

## Instalação

Pré-requisitos: Python 3.10+.

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate

pip install -r requirements.txt
```

## Rodando os testes

```bash
pytest -q
```

## Preparando o dataset (Etapa 1.1)

Baixa o [Medical Abstracts TC Corpus](https://github.com/sebischair/Medical-Abstracts-TC-Corpus),
limpa os dados, mapeia as classes clínicas originais para `normal` /
`atencao` / `urgente`, faz o split treino/teste e gera as amostras de
benchmark:

```bash
python -m src.prepare_dataset --seed 42 --test-size 0.2 --benchmark-per-class 15
```

Saídas geradas:

- `data/processed/train.csv`, `data/processed/test.csv`
- `data/benchmark_samples.json`
- `docs/dataset_distribution.md` (relatório de limpeza e distribuição de classes)

Detalhes sobre a fonte do dataset e o critério de mapeamento de classes:
ver [docs/dataset.md](docs/dataset.md).

## Licença

Uso acadêmico (Tech Challenge FIAP). Dataset original sob a licença do
repositório [Medical-Abstracts-TC-Corpus](https://github.com/sebischair/Medical-Abstracts-TC-Corpus).
