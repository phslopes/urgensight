# UrgenSight

[![CI](https://github.com/Edwardmaster7/urgensight/actions/workflows/ci.yml/badge.svg)](https://github.com/Edwardmaster7/urgensight/actions/workflows/ci.yml)

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
2. Instala `requirements.txt` em uma camada própria (otimiza cache de build).
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

## Licença

Uso acadêmico (Tech Challenge FIAP). Dataset original sob a licença do
repositório [Medical-Abstracts-TC-Corpus](https://github.com/sebischair/Medical-Abstracts-TC-Corpus).
