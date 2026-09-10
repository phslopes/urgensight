# UrgenSight

[![CI](https://github.com/Edwardmaster7/urgensight/actions/workflows/ci.yml/badge.svg)](https://github.com/Edwardmaster7/urgensight/actions/workflows/ci.yml)

Sistema de triagem automática de exames de texto (laudos médicos) para
classificação de urgência em 3 classes: `normal`, `atencao`, `urgente`.
Projeto acadêmico (Tech Challenge — FIAP MLET).

## Sumário

- [Status](#status)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Instalação](#instalação)
- [Rodando os testes](#rodando-os-testes)
- [Preparando o dataset (Etapa 1.1)](#preparando-o-dataset-etapa-11)
- [Treinando o modelo baseline (Etapa 1.2)](#treinando-o-modelo-baseline-etapa-12)
- [DAG de retreino no Airflow (Etapa 1.3)](#dag-de-retreino-no-airflow-etapa-13)
  - [Subir o ambiente](#subir-o-ambiente)
  - [Acessar a interface](#acessar-a-interface)
  - [Disparar a DAG](#disparar-a-dag)
  - [Nota: consistência de versões entre ambientes](#nota-consistência-de-versões-entre-ambientes)
  - [Encerrar o ambiente](#encerrar-o-ambiente)
- [Pipeline de dados com DVC](#pipeline-de-dados-com-dvc)
  - [Obter os dados e o modelo](#obter-os-dados-e-o-modelo)
  - [Reproduzir o pipeline](#reproduzir-o-pipeline)
  - [Experimentar sem editar `params.yaml`](#experimentar-sem-editar-paramsyaml)
  - [Publicar artefatos](#publicar-artefatos)
- [API de inferência (Etapa 2)](#api-de-inferência-etapa-2)
  - [Rodando localmente (sem Docker)](#rodando-localmente-sem-docker)
  - [Build da imagem Docker](#build-da-imagem-docker)
  - [Subir o container](#subir-o-container)
  - [Validar os endpoints](#validar-os-endpoints)
  - [Explorando as classificações (um exemplo por classe)](#explorando-as-classificações-um-exemplo-por-classe)
  - [Logs e parada](#logs-e-parada)
  - [Medição de latência baseline](#medição-de-latência-baseline)
  - [Nota: reproducibilidade do `model.pkl`](#nota-reproducibilidade-do-modelpkl)
- [Decisão Arquitetural em Nuvem](#decisão-arquitetural-em-nuvem)
  - [Análise de Processamento: Batch vs. Real-time](#análise-de-processamento-batch-vs-real-time)
  - [Provedor de Referência: AWS](#provedor-de-referência-aws)
  - [Desenho Lógico AWS](#desenho-lógico-aws)
  - [Disclaimer](#disclaimer)
- [Testes e Lint (Etapa 3)](#testes-e-lint-etapa-3)
- [CI/CD (Etapa 3)](#cicd-etapa-3)
- [Monitoramento (Etapa 3)](#monitoramento-etapa-3)
- [Otimização de latência (Etapa 4)](#otimização-de-latência-etapa-4)
  - [Resultados](#resultados)
  - [Backend ONNX na API (opcional)](#backend-onnx-na-api-opcional)
- [Licença](#licença)

## Status

- [x] Etapa 1 — Dataset, modelo baseline e DAG Airflow
- [x] Etapa 2 — API FastAPI, Docker e decisão arquitetural
- [x] Etapa 3 — Testes, CI/CD e observabilidade
- [x] Etapa 4 — Otimização de latência e benchmark

## Estrutura do projeto

```
data/
  raw/            # CSVs originais baixados (não versionado)
  processed/      # train.csv / test.csv gerados (não versionado)
  benchmark_samples.json  # amostras fixas para teste/benchmark (versionado)
src/
  prepare_dataset.py      # download, limpeza, mapeamento e split do dataset
  train.py                 # treino, avaliação e serialização do modelo baseline
  onnx_inference.py         # backend de inferencia via ONNX Runtime (Etapa 4, opcional)
tests/
  test_prepare_dataset.py # testes automatizados (pytest)
  test_train.py            # testes automatizados do pipeline de treino (pytest)
  test_model_loading.py    # validação isolada do carregamento de models/model.pkl
models/
  model.pkl                # pipeline serializado (vetorizador + modelo, não versionado)
  model.onnx                # versao otimizada via ONNX Runtime (Etapa 4, não versionado)
scripts/
  generate_load.py          # gera trafego sintetico contra POST /predict (Etapa 3)
  convert_to_onnx.py         # converte models/model.pkl -> models/model.onnx (Etapa 4)
  benchmark_latency.py       # compara latencia: modelo original vs. ONNX (Etapa 4)
docs/
  dataset.md               # fonte, formato e mapeamento de classes
  dataset_distribution.md  # relatório gerado automaticamente (Etapa 1.1)
  model_metrics.md         # métricas do modelo baseline (Etapa 1.2 / atualizado a cada run da DAG)
  airflow_run_evidence.png # print de uma execução bem-sucedida da DAG (Etapa 1.3)
  latency_results.md       # benchmark original vs. ONNX + instruções de integração (Etapa 4)
dags/
  train_pipeline.py        # DAG de retreino: carregamento -> treino -> salvamento
docker-compose.yml         # stack de monitoramento (API + Prometheus + Grafana)
docker-compose.airflow.yml # ambiente local do Airflow (Postgres + webserver + scheduler)
Dockerfile                 # imagem da API de inferencia
Dockerfile.airflow         # imagem do Airflow (nao e a imagem da API)
pyproject.toml         # dependencias, grupos e configuracao de ruff/pytest
uv.lock                # versoes exatas (fonte de verdade)
params.yaml   # hiperparametros do pipeline (fonte unica)
dvc.yaml      # estagios: download -> prepare -> train
dvc.lock      # hashes dos dados/modelo de cada execucao
.dvcstore/    # remote local do DVC (nao versionado)
```

## Instalação

Pré-requisitos: Python 3.12+ e [uv](https://docs.astral.sh/uv/) (o arquivo
`.python-version` fixa `3.12`; ver [ADR-0007](docs/ai/adr/0007-uv-com-lock-unico.md)).

```bash
# instalar o uv (uma vez)
curl -LsSf https://astral.sh/uv/install.sh | sh

# criar o ambiente e instalar tudo (dev + pipeline)
uv sync
```

`uv sync` lê `pyproject.toml` e `uv.lock`, cria o `.venv` e instala as
versões exatas do lock. Não é necessário ativar o ambiente: `uv run <comando>`
e os alvos do `Makefile` já executam dentro dele.

O projeto declara três conjuntos de dependências:

| Conjunto | Conteúdo | Instalação |
|---|---|---|
| `[project.dependencies]` | runtime da API (inclui `pandas`/`requests` — cadeia de imports `src.app -> src.train -> src.prepare_dataset`, ver ADR-0007) | `uv sync --no-default-groups` |
| grupo `pipeline` | `dvc` (uso local: `uv run dvc ...`) | `uv sync --no-default-groups --group pipeline` |
| grupo `dev` (padrão) | pytest, ruff, httpx + `pipeline` | `uv sync` |

## Rodando os testes

```bash
make test
```

## Preparando o dataset (Etapa 1.1)

Baixa o [Medical Abstracts TC Corpus](https://github.com/sebischair/Medical-Abstracts-TC-Corpus),
limpa os dados, mapeia as classes clínicas originais para `normal` /
`atencao` / `urgente`, faz o split treino/teste e gera as amostras de
benchmark:

```bash
uv run dvc repro prepare
```

Caminho recomendado: reaproveita o cache do DVC (não repete o download se
`data/raw` já estiver presente e inalterado). O comando direto continua
funcionando como alternativa:

```bash
uv run python -m src.prepare_dataset --seed 42 --test-size 0.2 --benchmark-per-class 15
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
uv run dvc repro train
```

Caminho recomendado: reaproveita o cache do DVC — se `data/processed` não
mudou desde a última execução, só o estágio `train` roda. Os hiperparâmetros
vêm de `params.yaml`. O comando direto continua funcionando como
alternativa:

```bash
uv run python -m src.train --model logreg --seed 42
```

Opções disponíveis: `--train-path`, `--test-path`, `--model-out`,
`--metrics-out`, `--model {logreg,linear_svc}`, `--seed`, `--max-features`.

Saídas geradas:

- `models/model.pkl` — pipeline completo (vetorizador TF-IDF + modelo) serializado via `joblib`
- `docs/model_metrics.md` — accuracy, F1 macro/weighted, F1 por classe, matriz de confusão e nota de compatibilidade com ONNX

Para validar isoladamente que o modelo salvo carrega e prediz corretamente
sobre as amostras de benchmark:

```bash
uv run pytest tests/test_model_loading.py -v
```

## DAG de retreino no Airflow (Etapa 1.3)

Pré-requisitos: [Docker Desktop](https://www.docker.com/products/docker-desktop/)
instalado e em execução, e o dataset já processado (rode a Etapa 1.1 antes:
`uv run python -m src.prepare_dataset`).

A DAG `train_pipeline` simula um fluxo de retreino agendado (`@weekly`) com
3 tasks, na ordem obrigatória `carregamento/validação dos dados → treino →
salvamento do modelo`. Cada task chama os estágios do pipeline DVC
(`dvc repro prepare`, `dvc repro train`, `dvc push`) via subprocess — a
lógica de dados e treino mora em `dvc.yaml`, que por sua vez chama
`src/prepare_dataset.py` e `src/train.py` (ver seção
["Pipeline de dados com DVC"](#pipeline-de-dados-com-dvc)). A cada execução,
o modelo treinado é promovido para `models/model.pkl` e uma cópia
versionada por timestamp é salva em `models/history/`.

### Subir o ambiente

```bash
make dev-airflow
# equivalente a: docker compose -f docker-compose.airflow.yml up -d --build
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
docker compose -f docker-compose.airflow.yml exec airflow-webserver \
  airflow dags trigger train_pipeline
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
`dill` instalado. Por isso `dill` está declarado em `[project.dependencies]`
(runtime, não só dev), o `scikit-learn` está fixado em `==1.5.1` (evitando o
`InconsistentVersionWarning` ao desserializar um modelo treinado em outra
versão) e o `numpy` está fixado em `==1.26.4` — mesma versão das constraints
oficiais do Airflow, que é o ambiente menos flexível dos dois. Qualquer
ambiente que for carregar `models/model.pkl` (ex.: a API da Etapa 2) deve
instalar as mesmas versões declaradas em `pyproject.toml` e fixadas em
`uv.lock` (ver [ADR-0007](docs/ai/adr/0007-uv-com-lock-unico.md)).

### Encerrar o ambiente

```bash
docker compose -f docker-compose.airflow.yml down

# reset completo do metastore (remove o volume do Postgres)
docker compose -f docker-compose.airflow.yml down -v
```

## Pipeline de dados com DVC

O pipeline de dados e treino é declarado em `dvc.yaml`, com três estágios:

```
download  →  prepare  →  train
data/raw     data/processed   models/model.pkl
             benchmark_samples.json   docs/model_metrics.{md,json}
             docs/dataset_distribution.md
```

Os hiperparâmetros ficam em `params.yaml` — fonte única, consumida tanto pela
execução local quanto pela DAG do Airflow.

### Obter os dados e o modelo

```bash
uv run dvc pull
```

Baixa `data/` e `models/model.pkl` do remote local (`.dvcstore/`) na versão
correspondente ao commit atual — **reaproveitando o cache já existente na
mesma máquina**, sem re-treinar nem reprocessar nada. `.dvcstore/` está no
`.gitignore`: existe só na máquina onde alguém rodou `dvc push`, não é
publicado junto com o repositório. Numa máquina nova (clone limpo, sem
`.dvcstore/` local), `dvc pull` não tem de onde baixar; o primeiro
`uv run dvc repro` ainda faz o download original do corpus em
`raw.githubusercontent.com` (estágio `download`). O valor do remote local é
reuso de cache/reprodutibilidade na mesma máquina entre execuções, não
eliminar essa dependência externa para todo o time.

### Reproduzir o pipeline

```bash
uv run dvc repro
```

O DVC reexecuta **apenas** os estágios afetados. Alterar
`train.max_features` em `params.yaml` retreina o modelo sem reprocessar os
17 MB de `data/raw`.

### Experimentar sem editar `params.yaml`

```bash
uv run dvc exp run -S train.max_features=500
uv run dvc metrics diff
```

### Publicar artefatos

```bash
uv run dvc push
```

## API de inferência (Etapa 2)

A API FastAPI serve o pipeline serializado em `models/model.pkl` via
`POST /predict`. O modelo é carregado em memória uma única vez no startup
(lifespan) e reutilizado por todas as requisições. Se o modelo estiver
ausente ou inválido, a API inicia mesmo assim e responde `503 Service
Unavailable` em `/predict` e `/health` até que um modelo válido esteja
presente. Contrato formal: [docs/api_contract.md](docs/api_contract.md).

### Rodando localmente (sem Docker)

```bash
uvicorn src.app:app --host 0.0.0.0 --port 8000
```

Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs).

### Build da imagem Docker

O `Dockerfile` da API executa os seguintes passos:

1. Parte de `python:3.12-slim` (mesmo major/minor usado no ambiente de dev,
   garantindo compatibilidade com o pickle do modelo).
2. Instala as dependências de runtime com `uv sync --frozen
   --no-default-groups` em uma camada própria (otimiza cache de build).
3. Copia `src/` e o artefato `models/model.pkl`.
4. Executa como usuário não-root (`appuser`).
5. Expõe a porta `8000` e sobe o Uvicorn em `src.app:app`.
6. Registra um `HEALTHCHECK` que falha quando o modelo não está carregado.

```bash
docker build -t urgensight-api .
```

### Subir o container

```bash
docker run -d -p 8000:8000 --name urgensight-api urgensight-api
```

Aguardar o health check ficar `healthy`:

```bash
docker inspect --format='{{.State.Health.Status}}' urgensight-api
```

### Validar os endpoints

```bash
# Health check (200 quando o modelo esta carregado)
curl -s http://localhost:8000/health
# {"status":"ok","model_loaded":true}

# Predicao (inferencia real do modelo)
curl -s -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "Severe chest pain with dyspnea and diaphoresis, ECG shows ST elevation, suspect acute myocardial infarction."}'
# {"prediction":"urgente"}
```

Respostas esperadas sem modelo válido dentro da imagem:

```json
{"detail": "Modelo de ML indisponivel."}
```

### Explorando as classificações (um exemplo por classe)

> **Idioma: inglês.** O modelo foi treinado em um corpus academico
> exclusivamente em inglês (ver [`docs/dataset.md`](docs/dataset.md)), então
> é esse o idioma que o `TfidfVectorizer` reconhece. Texto em português cai,
> quase sempre, em `normal` — não é bug, ver
> [ADR-0009](docs/ai/adr/0009-idioma-ingles-como-contrato-efetivo-da-api.md).

Os três textos abaixo são amostras reais de `data/benchmark_samples.json`
(validadas via `curl` contra o modelo real) e cobrem uma predição de cada
classe:

> **Atenção:** o `TfidfVectorizer` é sensível ao texto completo — truncar um
> abstract pode mudar a classe prevista. Os exemplos abaixo estão na íntegra
> (como em `data/benchmark_samples.json`) e foram revalidados via `curl`
> contra o modelo real antes de entrarem aqui.

```bash
# -> {"prediction":"normal"}
curl -s -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "Extradural abscess following local anaesthetic and steroid injection for chronic low back pain. A case is described of extradural abscess following extradural injection of local anaesthetic and steroid for the management of chronic low back pain. The common signs and symptoms are reviewed, possible causes discussed and the association with diabetes stressed."}'

# -> {"prediction":"atencao"}
curl -s -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "Outpatient management of schizophrenia. As effective antipsychotic pharmacotherapy has become available, patients with schizophrenia are increasingly managed in an outpatient setting by primary care physicians. Pharmacotherapy is generally effective in treating positive, or psychotic, symptoms and lessening the risks of relapse, but ineffective in improving negative, or deficit, symptoms. Aggressive attempts to totally control positive symptoms and to ameliorate negative symptoms tend to increase side effects and may be detrimental to the patient. Intensive psychotherapeutic and rehabilitative approaches are generally unproductive. Attempting to obtain a cure is unrealistic. A moderate approach is recommended, taking into consideration the limitations of existing treatments, achieving control of extreme symptoms and minimizing social and occupational limitations."}'

# -> {"prediction":"urgente"}
curl -s -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "Misplaced caval filter and subsequent pericardial tamponade. Use of the Greenfield filter for partial caval interruption is generally accepted as the most reliable mechanical method of pulmonary embolus prophylaxis. However, there have been reports of a variety of (usually nonfatal) complications. We report here the near-fatal complication of acute pericardial tamponade after misplacement of a Greenfield filter. Because of the filter'"'"'s unusual location, retrieval required cardiopulmonary bypass, profound hyperthermia, and circulatory arrest."}'
```

Mais amostras por classe (15 de cada) estão disponíveis em
[`data/benchmark_samples.json`](data/benchmark_samples.json) para explorar
outros casos direto no Swagger UI (`http://localhost:8000/docs`).

### Logs e parada

```bash
docker logs -f urgensight-api
docker stop urgensight-api && docker rm urgensight-api
```

### Medição de latência baseline

```bash
# Instalar hey (macOS)
brew install hey

# Benchmark: 100 requisições, 4 conexões concorrentes
hey -n 100 -c 4 -m POST \
  -H "Content-Type: application/json" \
  -d '{"text": "Paciente apresenta tosse e febre. Necessita triagem urgente."}' \
  http://localhost:8000/predict
```

Resultados do baseline (Apple M4 Pro, Docker local): ver [`docs/baseline_latency.md`](docs/baseline_latency.md).

### Nota: reproducibilidade do `model.pkl`

O `Dockerfile` copia o `models/model.pkl` presente no contexto de build. Para
garantir que o artefato na imagem seja exatamente o esperado, o fluxo
recomendado de CI/CD é:

1. Treinar/validar o modelo no ambiente Airflow (Etapa 1.3).
2. Copiar o `model.pkl` validado para o workspace da API.
3. Rodar `docker build` — o artefato é congelado na imagem.
4. Publicar a imagem tagueada com o hash do commit (ex: `urgensight-api:a1b2c3d`).

Nunca montar `models/` como volume de desenvolvimento em produção: a imagem
deve ser auto-contida e imutável.

## Decisão Arquitetural em Nuvem

Esta seção documenta a fundamentação teórica para uma eventual implantação
da API UrgenSight em ambiente de produção na nuvem, considerando o contexto
de triagem de laudos hospitalares.

### Análise de Processamento: Batch vs. Real-time

A escolha do padrão de processamento deve refletir a natureza clínica do
problema. Um laudo classificado como `urgente` demanda ação humana em
minutos, não em horas. Isso direciona a decisão:

| Critério | Batch | Real-time |
|----------|-------|-----------|
| Latência por requisição | N/A (agregado, minutos a horas) | Millissegundos |
| Adequação ao contexto clínico | **Inadequado**: um caso urgente esperaria o próximo ciclo do batch | **Adequado**: resposta imediata na chegada do laudo |
| Complexidade operacional | Baixa (job agendado) | Média (serviço sempre ativo) |
| Custo computacional | Menor (recursos sob demanda) | Maior (instâncias sempre provisionadas) |
| Observabilidade | Agregada (métricas por lote) | Por requisição (SLA de 99.9%) |

**Estratégia recomendada: Real-time (síncrono HTTP)**. Para triagem
hospitalar, o requisito não-funcional dominante é o **tempo de detecção do
caso urgente**. Um pipeline batch introduziria um intervalo de espera
inaceitável entre a geração do laudo e a sinalização ao médico plantonista.
A latência alvo de < 200 ms (p99) é facilmente atingida pelo pipeline
TF-IDF + regressão logística (CPU-bound, sem I/O intensivo), tornando o
modelo real-time tecnicamente viável e clinicamente necessário.

Batch seria apropriado apenas como **camada secundária** — por exemplo, um
job noturno de reconciliação que processa laudos do dia para fins de BI e
auditoria de qualidade do modelo, sem impacto no fluxo clínico primário.

### Provedor de Referência: AWS

Selecionamos a **Amazon Web Services** pela maturidade do ecossistema de
contêineres, presença de regiões no Brasil (`sa-east-1`, para reduzir
latência com hospitais brasileiros) e pelo alinhamento com padrões de
conformidade em saúde (HIPAA, ISO 27001, e equivalentes brasileiros como a
LGPD).

### Desenho Lógico AWS

```
┌─────────────────────────────────────────────────────────────────┐
│                        AWS Cloud (sa-east-1)                     │
│                                                                 │
│  ┌──────────┐    ┌──────────────┐    ┌─────────────────────┐   │
│  │ Hospital │───►│  ALB / NLB   │───►│  ECS Fargate        │   │
│  │ (HTTPS)  │    │  (TLS term.) │    │  ┌───────────────┐  │   │
│  └──────────┘    └──────────────┘    │  │ urgensight-   │  │   │
│                                      │  │ api: latest   │  │   │
│                                      │  │ (2-10 tasks)  │  │   │
│                                      │  └───────────────┘  │   │
│                                      └─────────────────────┘   │
│                                                │               │
│                      ┌─────────────────────────┘               │
│                      ▼                                         │
│              ┌──────────────┐                                  │
│              │   ECR        │  (imagens Docker versionadas)    │
│              └──────────────┘                                  │
│                                                                 │
│  Observabilidade: CloudWatch (logs, métricas, alarmes)          │
│  Segredos:        Secrets Manager (nenhum segredo na imagem)    │
│  Rede:            VPC privada, subnets em 2 AZs, NAT Gateway    │
└─────────────────────────────────────────────────────────────────┘
```

**API de inferência (ECS Fargate + ALB)**

O Amazon ECS com Fargate elimina a gestão de servidores EC2, pagando
apenas pelas tasks em execução. Escalabilidade horizontal automática
baseada em CPU/memória (Target Tracking Scaling) acomoda picos de
demanda (ex: plantões noturnos). O Application Load Balancer distribui
tráfego entre tasks saudáveis em múltiplas AZs e encerra TLS com certificado
do ACM (AWS Certificate Manager).

**Alta disponibilidade e baixa latência**

- **Multi-AZ**: tasks distribuídas em pelo menos duas zonas de
  disponibilidade de `sa-east-1`; o Fargate substitui tasks não saudáveis
  automaticamente (health check do Dockerfile já expõe `/health`).
- **Auto Scaling**: alvo de 50% de utilização de CPU; sobe de 2 para 10
  tasks em ~60 segundos sob carga.
- **Latência**: região `sa-east-1` para minimizar RTT com hospitais
  brasileiros; TF-IDF + LR roda inteiramente em RAM (sem banco de dados
  no hot path), garantindo p99 < 50 ms dentro da task.

**Governança de dados clínicos (LGPD)**

- Laudos em trânsito: TLS 1.3 obrigatório no ALB.
- Laudos em repouso: se houver persistência para auditoria, utilizar S3
  com criptografia SSE-KMS e chave gerenciada dedicada.
- Logs do CloudWatch: desabilitar logging do corpo da requisição (payload
  do laudo) para não reter dados pessoais de saúde em texto plano.

**CI/CD sugerido**

Push para `main` → GitHub Actions → testes + análise de segurança →
`docker build` → push para ECR com tag do commit → `ecs update-service`
com rolling deployment. Rollback automático via CloudWatch alarmes
(erros 5xx > 1% por 5 minutos).

### Disclaimer

**O escopo deste projeto (Tech Challenge — FIAP MLET) foi focado na
engenharia da análise textual e na construção da API local containerizada.
A infraestrutura em nuvem descrita nesta seção é uma fundamentação
teórica de arquitetura e não contempla o provisionamento real,
configuração de redes, custos ou conformidade com órgãos reguladores
(ANVISA, CFM). Qualquer implantação em ambiente hospitalar real exigiria
avaliação jurídica, testes de penetração e validação clínica do modelo.**

## Testes e Lint (Etapa 3)

Além de `pytest -q` (seção acima), o projeto padroniza a execução via
Makefile:

```bash
make test       # roda toda a suite (python -m pytest)
make test-cov   # pytest com cobertura de codigo (--cov=src --cov-report=term-missing)
make lint       # ruff check src/ tests/ dags/
make format     # ruff format + ruff check --fix
```

`ruff` cuida de formatação, `isort` e lint em um único comando. A suíte de
testes cobre `src/prepare_dataset.py`, `src/train.py`, `src/app.py` e
`src/metrics.py` (instrumentação Prometheus), além de validar o carregamento
isolado do `models/model.pkl`.

## CI/CD (Etapa 3)

O pipeline definido em [`.github/workflows/ci.yml`](.github/workflows/ci.yml)
roda em todo `push` para `main`/`feat/**` e em todo `pull_request` para
`main`, com quatro jobs encadeados:

1. **Lint (ruff)** — `ruff check src/ tests/ dags/`.
2. **Testes (pytest)** — roda a suíte completa; os testes são mockados/usam
   fixtures e não dependem de `models/model.pkl` (`test_model_loading.py` faz
   skip automático quando o arquivo está ausente).
3. **Dummy training** — treina `src/train.py` de ponta a ponta sobre um
   fixture versionado (`tests/fixtures/sample_dataset.csv`), sem download
   externo, apenas para provar que o pipeline de treino roda no CI. O
   `model.pkl` gerado é publicado como artefato para o job seguinte.
4. **Build da imagem Docker** — baixa o artefato do job anterior e builda a
   imagem (`docker build`), sem publicar em nenhum registry.

`lint` e `test` rodam em paralelo; `smoke-train` e `build` dependem
(`needs`) dos anteriores, na ordem `lint ∥ test → smoke-train → build`.

## Monitoramento (Etapa 3)

Stack local de observabilidade via Docker Compose: API + Prometheus +
Grafana. **O Airflow (Etapa 1.3) agora sobe separadamente**, com
`make dev-airflow` (`docker-compose.airflow.yml`) — o `docker-compose.yml` da
raiz é exclusivo da stack de monitoramento.

```bash
make dev              # sobe API + Prometheus + Grafana (builda o modelo se necessario)
make load             # gera trafego real contra POST /predict
make monitoring-down  # derruba a stack
```

URLs:

- API (Swagger): [http://localhost:8000/docs](http://localhost:8000/docs)
- Prometheus (targets): [http://localhost:9090/targets](http://localhost:9090/targets)
- Grafana (dashboard, sem login — acesso anônimo em modo Viewer):
  [http://localhost:3000](http://localhost:3000)

O dashboard `monitoring/dashboard.json` é provisionado automaticamente ao
subir o Grafana, com 6 painéis: total de requisições, modelo carregado,
throughput (req/s), latência (p50/p95/p99), taxa de erro (não-2xx) e
predições por classe de urgência. `scripts/generate_load.py`
(`make load`, ou `python scripts/generate_load.py --duration <s> --rps <n>
--error-rate <0-1>`) gera tráfego sintético contra `/predict` — incluindo uma
fração configurável de payloads inválidos — para popular os painéis com
dados reais.

Detalhes da instrumentação (`src/metrics.py`), do contrato de métricas e das
evidências coletadas: [`docs/api_contract.md`](docs/api_contract.md) e
[`docs/monitoring_evidence.md`](docs/monitoring_evidence.md).

## Otimização de latência (Etapa 4)

Técnica aplicada: **conversão do pipeline treinado para ONNX Runtime**
(`skl2onnx`), conforme sinalizado como compatível desde a Etapa 1 (ver
`docs/model_metrics.md` e [ADR-0010](docs/ai/adr/0010-onnx-runtime-como-tecnica-de-otimizacao.md)).

```bash
# Instala as dependencias opcionais (skl2onnx + onnxruntime)
uv sync --group optimization

# Converte models/model.pkl -> models/model.onnx e valida paridade
# de predicoes contra as amostras de benchmark
make convert-onnx        # ou: python -m scripts.convert_to_onnx

# Mede latencia (modelo original vs. ONNX) e grava docs/latency_results.md
make benchmark-latency    # ou: python -m scripts.benchmark_latency
```

`models/model.onnx` não é versionado no git (mesmo tratamento de
`models/model.pkl` — regenerável, determinístico a partir do modelo
treinado).

### Resultados

Benchmark de latência de inferência por requisição (uma predição por
chamada, sem batching), 2000 execuções + 200 de aquecimento descartadas,
mesma máquina, mesmas 45 amostras de `data/benchmark_samples.json`:

| Modelo | Média (ms) | Mediana (ms) | p95 (ms) |
|---|---|---|---|
| Original (scikit-learn) | 0.682 | 0.644 | 1.017 |
| Otimizado (ONNX Runtime) | 0.215 | 0.196 | 0.388 |
| **Melhoria** | **+68.42%** | — | **+61.82%** |

Paridade de predições entre o modelo original e o otimizado: **100%**
nas 45 amostras de benchmark; **99.42%** (2233/2246) no conjunto de teste
completo — as 13 divergências são casos de probabilidade quase empatada
entre as duas classes mais prováveis (precisão `float32` do ONNX Runtime
vs. `float64` do scikit-learn perto do limiar de decisão), não erro de
conversão. Análise completa: [`docs/latency_results.md`](docs/latency_results.md).

> Este benchmark mede o backend de inferência isoladamente (sem HTTP/rede
> — não é comparável linha a linha com o baseline de
> [`docs/baseline_latency.md`](docs/baseline_latency.md), que mede a API
> completa em Docker via `hey`). Ver "Backend ONNX na API" abaixo para a
> medição ponta a ponta.

### Backend ONNX na API (opcional)

Com aval do Integrante 2, o backend ONNX foi integrado em `src/app.py`
atrás da variável de ambiente `MODEL_BACKEND` — o padrão (`sklearn` ou
ausente) preserva o comportamento original da Etapa 2 sem nenhuma
mudança. Ver [ADR-0011](docs/ai/adr/0011-integracao-opcional-do-onnx-na-api.md)
para o design e um bug de locale do ONNX Runtime encontrado e corrigido
no `Dockerfile`.

```bash
# Local (sem Docker)
uv sync --group api-onnx
MODEL_BACKEND=onnx uv run uvicorn src.app:app --reload

# Docker / Docker Compose
make convert-onnx                  # gera models/model.onnx antes do build
docker build -t urgensight-api .
docker run -p 8000:8000 -e MODEL_BACKEND=onnx urgensight-api
# ou: MODEL_BACKEND=onnx docker compose up --build
```

Medição ponta a ponta em Docker (`POST /predict`, mesma máquina, mesmo
payload): ganho de **~5-12%** — bem menor que o ~68% do modelo isolado,
porque overhead de HTTP/rede/validação não muda com o backend do modelo
e domina o tempo total num payload pequeno. Números completos e a
ressalva sobre por que não são comparáveis ao baseline da Etapa 2 (SO e
metodologia diferentes): [`docs/latency_results.md`](docs/latency_results.md#integração-na-api-realizada-opcional-via-model_backend).

## Licença

Uso acadêmico (Tech Challenge FIAP). Dataset original sob a licença do
repositório [Medical-Abstracts-TC-Corpus](https://github.com/sebischair/Medical-Abstracts-TC-Corpus).
