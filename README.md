# UrgenSight

Sistema de triagem automática de exames de texto (laudos médicos) para
classificação de urgência em 3 classes: `normal`, `atencao`, `urgente`.
Projeto acadêmico (Tech Challenge — FIAP MLET).

## Status

- [x] Etapa 1.1 — Dataset e preparação
- [x] Etapa 1.2 — Modelo baseline
- [x] Etapa 1.3 — DAG Airflow

## Estrutura do projeto

```
data/
  raw/            # CSVs originais baixados (não versionado)
  processed/      # train.csv / test.csv gerados (não versionado)
  benchmark_samples.json  # amostras fixas para teste/benchmark (versionado)
src/
  prepare_dataset.py      # download, limpeza, mapeamento e split do dataset
  train.py                 # treino, avaliação e serialização do modelo baseline
tests/
  test_prepare_dataset.py # testes automatizados (pytest)
  test_train.py            # testes automatizados do pipeline de treino (pytest)
  test_model_loading.py    # validação isolada do carregamento de models/model.pkl
models/
  model.pkl                # pipeline serializado (vetorizador + modelo, não versionado)
docs/
  dataset.md               # fonte, formato e mapeamento de classes
  dataset_distribution.md  # relatório gerado automaticamente (Etapa 1.1)
  model_metrics.md         # métricas do modelo baseline (Etapa 1.2 / atualizado a cada run da DAG)
  airflow_run_evidence.png # print de uma execução bem-sucedida da DAG (Etapa 1.3)
dags/
  train_pipeline.py        # DAG de retreino: carregamento -> treino -> salvamento
docker-compose.yml    # ambiente local do Airflow (Postgres + webserver + scheduler)
Dockerfile.airflow    # imagem do Airflow usada pelo docker-compose (não é a imagem da API)
requirements.txt      # dependências de runtime (também instaladas na imagem do Airflow)
requirements-dev.txt  # requirements.txt + pytest (uso local)
```

## Instalação

Pré-requisitos: Python 3.10+.

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate

pip install -r requirements-dev.txt
```

`requirements.txt` contém só as dependências de runtime (usadas também
dentro da imagem do Airflow); `requirements-dev.txt` adiciona o `pytest`
para rodar os testes localmente.

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

## Treinando o modelo baseline (Etapa 1.2)

Treina um pipeline TF-IDF + classificador leve (Logistic Regression por
padrão, ou Linear SVC) sobre o dataset processado, avalia accuracy e F1 por
classe e serializa o pipeline completo:

```bash
python -m src.train --model logreg --seed 42
```

Opções disponíveis: `--train-path`, `--test-path`, `--model-out`,
`--metrics-out`, `--model {logreg,linear_svc}`, `--seed`, `--max-features`.

Saídas geradas:

- `models/model.pkl` — pipeline completo (vetorizador TF-IDF + modelo) serializado via `joblib`
- `docs/model_metrics.md` — accuracy, F1 macro/weighted, F1 por classe, matriz de confusão e nota de compatibilidade com ONNX

Para validar isoladamente que o modelo salvo carrega e prediz corretamente
sobre as amostras de benchmark:

```bash
pytest tests/test_model_loading.py -v
```

## DAG de retreino no Airflow (Etapa 1.3)

Pré-requisitos: [Docker Desktop](https://www.docker.com/products/docker-desktop/)
instalado e em execução, e o dataset já processado (rode a Etapa 1.1 antes:
`python -m src.prepare_dataset`).

A DAG `train_pipeline` simula um fluxo de retreino agendado (`@weekly`) com
3 tasks, na ordem obrigatória `carregamento/validação dos dados → treino →
salvamento do modelo`, reutilizando diretamente as funções de
`src/prepare_dataset.py` e `src/train.py` (nenhuma lógica é duplicada). A
cada execução, o modelo treinado é promovido para `models/model.pkl` e uma
cópia versionada por timestamp é salva em `models/history/`.

### Subir o ambiente

```bash
docker compose up -d --build
```

Isso builda a imagem `Dockerfile.airflow` (Airflow + dependências do
projeto), sobe o Postgres (metastore do Airflow) e inicializa o banco e o
usuário administrador (`admin` / `admin`).

### Acessar a interface

Abra [http://localhost:8080](http://localhost:8080) e faça login com
`admin` / `admin`.

### Disparar a DAG

Pela interface: localize `train_pipeline` na lista de DAGs, ative o toggle
(unpause) e clique em **Trigger DAG** (▶). Ou via linha de comando:

```bash
docker compose exec airflow-webserver airflow dags trigger train_pipeline
```

Acompanhe o progresso na visão **Graph** ou **Grid** da DAG. Os logs de
cada task ficam disponíveis na interface e também em `airflow_logs/`
(bind mount, não versionado).

Evidência de uma execução bem-sucedida (3/3 tasks verdes, na ordem
`load_and_validate_data → train_model → save_model`):
[docs/airflow_run_evidence.png](docs/airflow_run_evidence.png).

### Nota: consistência de versões entre ambientes

O `apache-airflow` traz `dill` como dependência transitiva, e isso faz o
`pickle` do Python usar handlers do `dill` para alguns objetos durante o
`joblib.dump` — ou seja, um `model.pkl` treinado **dentro do container**
Airflow só recarrega em outro ambiente se esse ambiente também tiver
`dill` instalado. Por isso `dill` está declarado em `requirements.txt`
(runtime, não só dev) e o `scikit-learn` está fixado em `==1.5.1` (tanto
localmente quanto na imagem do Airflow), evitando o
`InconsistentVersionWarning` do scikit-learn ao desserializar um modelo
treinado em outra versão. Qualquer ambiente que for carregar
`models/model.pkl` (ex.: a API da Etapa 2) deve instalar as mesmas
versões de `requirements.txt`.

### Encerrar o ambiente

```bash
docker compose down
```

Para remover também o volume do Postgres (reset completo do metastore):

```bash
docker compose down -v
```

## Licença

Uso acadêmico (Tech Challenge FIAP). Dataset original sob a licença do
repositório [Medical-Abstracts-TC-Corpus](https://github.com/sebischair/Medical-Abstracts-TC-Corpus).
