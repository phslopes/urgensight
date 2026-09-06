# Design — DVC, uv e Python 3.12 no UrgenSight

**Data:** 2026-09-02
**Status:** Proposto (aguardando revisão)
**Etapa:** 3 (adendo — não substitui o escopo já concluído)
**Fontes:** `Tech Challenge Fase 02.pdf` (Etapa 3), MOD5 — Controle de Dados e
Modelos (DVC e MLflow), Aulas 1, 2, 3 e 6; MOD3 — Gerenciamento de
Dependências, Aula 2; repositório em `4039485`.

---

## 1. Contexto

O UrgenSight é o Tech Challenge da **Fase 3** (`docs/specs/MLET - Tech
Challenge Fase 3.pdf`), cuja rubrica é: Modelagem/Otimização 20%, CI/CD 15%,
Airflow 15%, Monitoramento 20%, README 15%, Vídeo 15%. **DVC não pontua nesta
fase** — ele aparece na Fase 2 (`Tech Challenge Fase 02.pdf`, Etapa 3:
"DVC init, versionar dataset, configurar remote (local ou S3)... Pipeline DVC
(`dvc.yaml`): preprocess → feature_eng → train → evaluate").

A adoção aqui é, portanto, uma decisão de engenharia, justificada por três
problemas reais e verificados no repositório:

### 1.1. Três fontes de verdade para dependências

`pyproject.toml`, `requirements.txt`, `requirements-dev.txt` e `uv.lock`
coexistem. O `uv.lock` (498 KB) está commitado e **nenhum ambiente o usa**: o
CI, o `Dockerfile` e o `Dockerfile.airflow` instalam com `pip` a partir dos
`requirements*.txt`. Os comentários em `requirements-dev.txt:5-19` documentam
a cicatriz disso — o pacote inexistente `httpx2` e a ausência de `ruff`
passaram despercebidos localmente e só quebraram no CI.

### 1.2. Divergência de `numpy` entre treino e inferência (risco ativo)

| Ambiente | `numpy` | `pandas` | `dill` |
|---|---|---|---|
| `uv.lock` (commitado, não usado) | **2.2.6** | 2.3.3 | 0.4.1 |
| `requirements.txt` → API, Docker, CI | 1.26.x (teto `<2.0`) | 2.3.x | 0.3.x |
| `Dockerfile.airflow` (constraints oficiais 2.9.3) | **1.26.4** | **2.1.4** | 0.3.1.1 |

Pior: os constraints oficiais do Airflow **não listam** `scipy`,
`scikit-learn`, `joblib` nem `threadpoolctl` — exatamente os pacotes que o
`TfidfVectorizer` usa para serializar matrizes esparsas. Eles são resolvidos
de forma independente em cada ambiente hoje (`uv.lock` tem `scipy 1.15.3`; o
container do Airflow resolve o seu por conta). Um lock único é o único
mecanismo que fecha esse buraco, porque o `-c` do Airflow só restringe o que
ele próprio lista.

O modelo é **treinado** no container do Airflow e **servido** pela API. Hoje
isso só não quebra porque `requirements.txt:3` fixa `numpy>=1.26,<2.0`. Mas
`pyproject.toml:15` declara `numpy>=1.26.0` **sem teto**, e o `uv.lock` já
resolveu `numpy 2.2.6`. No momento em que `uv sync` virar a fonte de verdade,
essa proteção desaparece em silêncio e a API passará a desserializar, sob
`numpy` 2.x, um pipeline treinado sob `numpy` 1.26. É a mesma classe de
problema que o `CLAUDE.md` afirma resolvida via `dill` + `scikit-learn==1.5.1`
— só que `numpy` ficou de fora da conta.

### 1.3. Parâmetros duplicados em três lugares

| Origem | Parâmetros |
|---|---|
| `src/train.py:249-260` (`argparse`) | `model=logreg`, `seed=42`, `max_features=20000` |
| `dags/train_pipeline.py:63-68` (hardcoded) | `model_name="logreg"`, `seed=42` |
| `.github/workflows/ci.yml:56-62` | `--max-features 500`, fixture como dataset |

Não existe lugar único que responda "com quais parâmetros este modelo foi
treinado". O histórico em `models/history/model_<timestamp>.pkl`
(`dags/train_pipeline.py:110-118`) registra **quando** o modelo foi treinado,
mas não com quais dados, código ou hiperparâmetros.

---

## 2. Escopo

**Dentro:**

1. Piso de Python 3.12 em todo o projeto.
2. `uv` como único gerenciador de dependências, com grupos PEP 735.
3. DVC como pipeline reprodutível de dados e modelo, orquestrado pelo Airflow.
4. Auditoria e atualização de toda a documentação viva.
5. Três ADRs (0006, 0007, 0008).

**Fora:**

- MLflow (não pertence à rubrica da Fase 3 e dobraria o escopo).
- Pydantic Settings / `.env` (item da Fase 2, sem dor correspondente aqui).
- Refatoração de `src/` em `feature_eng` e `evaluate` separados.
- Remote em nuvem (S3/GCS) — exigiria credenciais e secret no CI.
- Qualquer alteração no escopo da Etapa 4 (ONNX/benchmark).

---

## 3. Decisões

| # | Decisão | Escolha |
|---|---|---|
| Q1 | Objetivo do DVC | Resolver duplicação de parâmetros + proteger reprodutibilidade contra dependência de download externo |
| Q2 | Fronteira DVC × Airflow | DVC é dono do pipeline; cada task da DAG chama `dvc repro <stage>` |
| Q3 | Artefatos sob DVC | `data/raw`, `data/processed`, `models/model.pkl` como *outputs de stages*; `models/history/` fica fora |
| Q4 | Perfis de parâmetros | `params.yaml` único; variação pontual via `dvc exp run -S` |
| Q5 | uv | Substitui o pip em **todas** as etapas, com grupos PEP 735 |
| Q6/Q7 | Python | Piso 3.12 em todo o projeto, incluindo Airflow (`2.9.3-python3.12`), com portão de validação |
| Q8 | Stages | Três: `download` → `prepare` → `train` |
| Q9 | DVC no CI | CI não roda `dvc repro`; consistência do lock verificada por teste da suíte (ver §6, R5) |
| Q10 | Métricas | `src/train.py` passa a emitir **também** `docs/model_metrics.json` |
| Q11 | Sequência | Tudo na Etapa 3, com gate de aborto para o DVC |
| Q12 | ADRs | Três: 0006 (DVC), 0007 (uv), 0008 (Python 3.12) |
| Q13 | Conflito de versões | `pyproject.toml` alinha ao piso do Airflow: `numpy==1.26.4`, `pandas==2.1.4` |
| Q14 | Remote do DVC | `.dvcstore/` dentro do repositório (gitignored) |
| Q15 | Mapeamento DAG → stages | `task_id` preservados; muda apenas o corpo das tasks |
| Q16 | Gate de aborto | Por resultado + por complexidade, com commits separados e revertíveis |
| Q17 | Injeção de params | `dvc.yaml` injeta na linha de comando; `src/` permanece agnóstico ao DVC |
| Q18 | Grupos de dependências | Divisão estrita, seguindo os imports reais |
| Q19 | `requirements*.txt` | Deletados |
| Q20 | uv obrigatório | Sim, sem fallback no Makefile |

### 3.1. Decisões derivadas (não passaram por pergunta explícita)

- **D1** — `src/prepare_dataset.py` ganha as flags `--download-only` e
  `--skip-download`. São necessárias para partir o script em dois stages
  (Q8) mantendo `argparse` como interface pública (Q17).
- **D2** — Artefatos hoje versionados no Git (`data/benchmark_samples.json`,
  `docs/dataset_distribution.md`, `docs/model_metrics.md`) são declarados como
  `outs` com **`cache: false`**. Continuam no Git exatamente como hoje; o DVC
  apenas passa a conhecê-los como saídas de stage.
- **D3** — `docs/model_metrics.json` é o caminho do artefato de métricas (Q10),
  também `cache: false`, para que `dvc metrics diff` funcione entre commits.
- **D4** — `.dvcstore/` e `/.dvc/cache` entram no `.gitignore` e no
  `.dockerignore`.
- **D5** — `dvc` pertence ao grupo `pipeline`: entra na imagem do Airflow e no
  ambiente de dev, **nunca** na imagem da API.
- **D6** — `pyproject.toml` ganha `[tool.uv] package = false`, tornando
  explícito o que o `uv.lock:1604` já registra (`source = { virtual = "." }`).

---

## 4. Arquitetura resultante

### 4.1. Camadas (conforme MOD5, Aula 2)

```
Git         código, dvc.yaml, params.yaml, dvc.lock, pyproject.toml, uv.lock
DVC         hashes, cache local, stages
.dvcstore/  dados e modelos (remote local, gitignored)
Airflow     agenda (@weekly), retries, UI  →  dispara dvc repro
```

Airflow e DVC não competem: o Airflow responde **quando** retreinar e prova
isso na UI (critério de 15% da rubrica); o DVC responde **o que precisa ser
refeito** e **qual versão saiu**.

### 4.2. `params.yaml`

```yaml
prepare:
  seed: 42
  test_size: 0.2
  benchmark_per_class: 15

train:
  model: logreg
  seed: 42
  max_features: 20000
```

Apenas knobs. Caminhos são responsabilidade do `dvc.yaml`.

### 4.3. `dvc.yaml`

```yaml
stages:
  download:
    cmd: python -m src.prepare_dataset --download-only --data-dir data
    deps:
      - src/prepare_dataset.py
    outs:
      - data/raw

  prepare:
    cmd: >-
      python -m src.prepare_dataset --skip-download --data-dir data
      --seed ${prepare.seed}
      --test-size ${prepare.test_size}
      --benchmark-per-class ${prepare.benchmark_per_class}
    deps:
      - src/prepare_dataset.py
      - data/raw
    params:
      - prepare
    outs:
      - data/processed
      - data/benchmark_samples.json:
          cache: false
      - docs/dataset_distribution.md:
          cache: false

  train:
    cmd: >-
      python -m src.train --model ${train.model}
      --seed ${train.seed}
      --max-features ${train.max_features}
    deps:
      - src/train.py
      - src/prepare_dataset.py
      - data/processed
    params:
      - train
    outs:
      - models/model.pkl
      - docs/model_metrics.md:
          cache: false
    metrics:
      - docs/model_metrics.json:
          cache: false
```

`params:` declarado por stage é o que faz o DVC incluir os hiperparâmetros no
hash de dependências — mudar `train.max_features` invalida só o stage `train`,
sem reprocessar os 17 MB de `data/raw` (MOD5, Aula 6).

### 4.4. Grupos de dependências (`pyproject.toml`)

```toml
[project]
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115.0",
  "uvicorn[standard]>=0.30.0",
  "pydantic>=2.8.0",
  "prometheus-client>=0.20",
  "scikit-learn==1.5.1",
  "joblib>=1.4.0",
  "numpy==1.26.4",
  "dill>=0.3.8",
]

[dependency-groups]
pipeline = ["pandas==2.1.4", "requests>=2.31.0", "dvc>=3.67"]
dev = [
  "pytest>=8.0.0", "pytest-asyncio>=0.23.0", "pytest-cov>=5.0.0",
  "ruff>=0.6.0", "httpx>=0.27.0",
  {include-group = "pipeline"},
]

[tool.uv]
package = false
```

Justificativa por import verificado: `src/app.py` não importa `pandas` nem
`requests`; `pandas` aparece só em `src/prepare_dataset.py:16` e
`src/train.py:18`; `requests` em `src/prepare_dataset.py:17` e
`scripts/generate_load.py:18`; `httpx` só em `tests/conftest.py:2`.

`numpy` e `pandas` ficam **fixados no piso do Airflow** (Q13): o ambiente menos
flexível dita a versão, e é isso que torna "uma fonte de verdade" literal.

### 4.5. Matriz de instalação

| Ambiente | Comando |
|---|---|
| Dev local | `uv sync` (grupo `dev` é default, inclui `pipeline`) |
| CI — lint/test | `uv sync --frozen` |
| CI — smoke-train | `uv sync --frozen --no-default-groups --group pipeline` |
| `Dockerfile` (API) | `uv sync --frozen --no-default-groups` |
| `Dockerfile.airflow` | `uv export --frozen --no-default-groups --group pipeline` + `uv pip install --system -c https://raw.githubusercontent.com/apache/airflow/constraints-2.9.3/constraints-3.12.txt` |

O `-c` com as constraints oficiais do Airflow é mantido e foi validado: sem
ele, `pandas>=2.1.4` resolve para `3.0.5`; com ele, para `2.1.4`. Também foi
validado que o `uv pip install` aceita `-c` por **URL**, não só por arquivo
local. Após o Q13 ele protege apenas as transitivas do próprio Airflow —
`scipy`, `scikit-learn` e `joblib` passam a vir do `uv.lock`, que é onde
deveriam estar desde sempre (§1.2).

### 4.6. Mapeamento DAG → stages

| `task_id` (preservado) | Corpo novo |
|---|---|
| `load_and_validate_data` | `dvc repro prepare` (arrasta `download` se necessário) |
| `train_model` | `dvc repro train` |
| `save_model` | `dvc push` + promoção para `models/model.pkl` + histórico |

Os quatro testes de `tests/test_train_pipeline_dag.py` continuam passando sem
edição — sinal de que a mudança é interna. O vocabulário da rubrica
("carregamento → treino → salvamento") é preservado.

O container do Airflow já enxerga cache e remote sem mount novo:
`docker-compose.airflow.yml:20` monta `.:/opt/airflow/project`.

---

## 5. Mudanças por arquivo

### 5.1. Commit 1 — Python 3.12

| Arquivo | Mudança |
|---|---|
| `pyproject.toml` | `requires-python = ">=3.12"`, `target-version = "py312"`, `[tool.uv] package = false` |
| `.python-version` | Criado: `3.12` |
| `Dockerfile.airflow` | `2.9.3-python3.11` → `2.9.3-python3.12`, `constraints-3.11.txt` → `constraints-3.12.txt` |
| `uv.lock` | Relock |

Tag e constraints já verificados como existentes (`2.9.3-python3.12` no Docker
Hub; `constraints-3.12.txt` HTTP 200; `numpy==1.26.4` e `pandas==2.1.4` em
ambos).

### 5.2. Commit 2 — uv

| Arquivo | Mudança |
|---|---|
| `pyproject.toml` | Grupos PEP 735 (§4.4); `numpy==1.26.4`, `pandas==2.1.4`; remove `[project.optional-dependencies]` |
| `requirements.txt`, `requirements-dev.txt` | **Deletados** |
| `.github/workflows/ci.yml` | `astral-sh/setup-uv@v6` + `uv sync --frozen`; remove `cache: pip` |
| `Dockerfile` | `uv sync --frozen --no-default-groups` |
| `Dockerfile.airflow` | `uv export` + `uv pip install --system -c <constraints>` |
| `Makefile` | `PYTHON = uv run python` sem fallback; erro explícito se `uv` ausente |
| `uv.lock` | Relock |

### 5.3. Commit 3 — DVC (revertível)

| Arquivo | Mudança |
|---|---|
| `params.yaml` | Criado (§4.2) |
| `dvc.yaml`, `dvc.lock` | Criados (§4.3) |
| `.dvc/config` | Remote local `.dvcstore/` |
| `src/prepare_dataset.py` | Flags `--download-only` / `--skip-download` (D1) |
| `src/train.py` | Emite `docs/model_metrics.json` além do `.md` (D3) |
| `dags/train_pipeline.py` | Corpo das tasks chama `dvc repro` (§4.6) |
| `tests/test_environment_consistency.py` | Classe comparando os params gravados em `dvc.lock` com `params.yaml` |
| `.gitignore`, `.dockerignore` | `.dvcstore/`, `/.dvc/cache` (D4) |
| `tests/test_prepare_dataset.py`, `tests/test_train.py` | Cobertura das flags novas e do JSON de métricas |

---

## 6. Riscos e gate de aborto

| # | Risco | Mitigação |
|---|---|---|
| R1 | Providers do Airflow não resolvem sob `constraints-3.12` | Portão do Q7: build + `make dev-airflow` + trigger da DAG antes do commit. Se falhar, Airflow permanece em 3.11 e a assimetria vira consequência registrada na ADR-0008 |
| R2 | API sem `pandas` falha ao desserializar o pickle | `tests/test_model_loading.py` + `HEALTHCHECK` (`Dockerfile:33-35`) falham o container. Se ocorrer, `pandas` volta ao runtime e vira consequência na ADR-0007 |
| R3 | `pandas 2.1.4` / `numpy 1.26.4` são versões antigas | Aceito conscientemente: é o preço de um único ambiente resolvido |
| R4 | DVC dentro do Airflow onera a DAG já entregue | Gate de aborto abaixo |
| R5 | Job `dvc-check` sem comando limpo para validar sem dados em cache | **Resolvido durante o planejamento:** não existe comando limpo (`dvc status` compara hashes de dependências ausentes), mas o `dvc.lock` grava os valores de params de cada estágio. A checagem virou teste de suíte por parsing de YAML — sem rede, sem cache, sem `dvc` no runner, e sem job novo no CI |

### 6.1. Gate de aborto do DVC (Q16 = A + C)

O commit 3 é **revertido** (`git revert`) se qualquer condição ocorrer:

- **Por resultado:** ao fim da implementação, `make test`, o CI e a DAG rodando
  localmente não estiverem os três verdes.
- **Por complexidade:** exigir alteração em `docker-compose.airflow.yml` ou
  em testes existentes que hoje passam.

A ordem dos commits (1 → 2 → 3) é o que torna esse gate executável: abortar o
DVC não desfaz o uv nem o Python 3.12.

---

## 7. Verificação

| Item | Como |
|---|---|
| Suíte verde | `make test` |
| Lint | `make lint` |
| Ambiente limpo reproduz | `rm -rf .venv && uv sync --frozen && make test` |
| API sem `pandas` sobe | `docker build -t urgensight-api . && docker run` + `/health` = 200 |
| Airflow 3.12 sobe | `make dev-airflow` + trigger da DAG + 3 tasks verdes |
| Pipeline DVC reproduz | `dvc repro` do zero, depois `dvc repro` de novo (deve reportar tudo *up to date*) |
| Cache seletivo funciona | Alterar `train.max_features` em `params.yaml` → só `train` reexecuta |
| Métricas comparáveis | `dvc metrics diff` entre dois commits |
| CI verde | Push na branch |

---

## 8. Auditoria de documentação

O pedido é aderência de 100%. A varredura encontrou divergências que **já
existem hoje**, independentes desta mudança:

| Arquivo | Linha | Divergência |
|---|---|---|
| `README.md` | 33 | Descreve `docker-compose.yml` como "ambiente local do Airflow" — hoje ele é a stack de monitoramento |
| `README.md` | 135, 156 | Manda `docker compose up -d --build` / `exec` para o Airflow, sem `-f docker-compose.airflow.yml` — comandos quebrados |
| `README.md` | 9-13 | Seção "Status" lista só as Etapas 1.1–1.3; Etapas 2 e 3 estão concluídas |
| `README.md` | 180-190 | "Encerrar o ambiente" (`docker compose down`) órfã da seção do Airflow |
| `README.md` | 40-41, 44-67, 172-178, 215 | `requirements*.txt`, `pip install`, "Python 3.10+", `python -m venv` |
| `CLAUDE.md` | seção Environment Isolation | Não menciona `numpy` na compatibilidade de pickle |
| `GEMINI.md` | 19 | "fixados em `requirements.txt`" |
| `docs/api_contract.md` | 159 | Mensagem de erro cita `requirements.txt` |
| `docs/ai/adr/0003` | — | Job `smoke-train` muda de `pip` para `uv`; adicionar link para a ADR-0007 (afetada, **não** superseded) |
| `docs/ai/adr/README.md` | — | Índice ganha 0006, 0007, 0008 |
| `docs/specs/phase-tracking.md` | Etapa 3 | Registrar o adendo e o estado do gate do DVC |
| `.dockerignore` | 2-3 | Comentário cita `requirements.txt` |

Tratados como **registro histórico e não reescritos**: `docs/ai/plans/*` e
`docs/ai/specs/2026-*` de etapas anteriores. Documentam o que foi decidido
naquele momento; reescrevê-los apagaria o histórico de decisão.

Cada commit atualiza a documentação que ele próprio invalida (assim o revert
do commit 3 leva junto a doc do DVC). As divergências pré-existentes do README
entram no commit 1.

### 8.1. Documentação nova

- `README.md`: seção "Pipeline de dados com DVC" (init, `dvc repro`, `dvc
  push/pull`, `params.yaml`, `dvc metrics diff`) e "Instalação" reescrita para
  `uv sync`.
- `docs/dataset.md`: como obter os dados via `dvc pull` em vez do download
  direto.

---

## 9. ADRs

| ADR | Título | Núcleo |
|---|---|---|
| 0006 | DVC como fonte de verdade do pipeline de treino | Alternativas: manter lógica na DAG; DVC substituindo o Airflow. Consequências: remote local em `.dvcstore/`, `dvc` na imagem do Airflow, `models/history/` mantido por ora |
| 0007 | uv com lock único e grupos PEP 735 | Alternativas: manter pip; uv exportando `requirements.txt`. Consequências: `numpy`/`pandas` fixados no piso do Airflow, `requirements*.txt` deletados, uv vira pré-requisito para o grupo, afeta a ADR-0003 |
| 0008 | Piso único de Python 3.12 | Alternativas: manter 3.10; subir Airflow para 2.10/2.11. Consequências: rebuild da imagem do Airflow, `.python-version` commitado |

Formato MADR, em PT-BR, conforme `docs/ai/adr/README.md`.

---

## 10. Fora de escopo (registrado para não se perder)

- `models/history/` continua com cópias por timestamp. Com o `dvc.lock` sob
  Git, isso passa a ser redundante — remover é uma decisão separada, para
  depois da entrega.
- MLflow, Pydantic Settings, remote em nuvem.
- A Etapa 4 (ONNX/benchmark) permanece intocada e continua sendo a maior
  pendência da rubrica (20%).
