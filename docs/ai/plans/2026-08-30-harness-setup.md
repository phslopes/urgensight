# Harness de Alta Maturidade (Nível 3) - Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar e configurar a arquitetura completa de Harness Dual (Claude Code e Gemini CLI) de Nível 3 para o projeto UrgenSight (FastAPI, Scikit-Learn, Airflow, Docker).

**Architecture:** Estruturação em 3 eixos (`.claude/`, `.gemini/`, `.agents/`), automação de lint/formatação zero-turn com Ruff e hooks, navegação por Knowledge Graph (`graphify`), governança com scripts de proteção e sincronização de memória, subagentes especializados para validação de ML/API e modernização da base de testes.

**Tech Stack:** Python 3.10+, uv, ruff, pytest, httpx, graphify, GNU Make, Bash, Git hooks.

---

### Task 1: Tooling & Configurações Base (`pyproject.toml`, `.graphifyignore`, `.ai-jail`)

**Files:**
- Create: `pyproject.toml`
- Create: `.graphifyignore`
- Create: `.ai-jail`

- [ ] **Step 1: Criar `pyproject.toml` com configurações do Ruff e Pytest**

```toml
[project]
name = "urgensight"
version = "0.1.0"
description = "Sistema de triagem automatica de exames de texto (laudos medicos)"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "pydantic>=2.8.0",
    "scikit-learn==1.5.1",
    "joblib>=1.4.0",
    "pandas>=2.2.0",
    "numpy>=1.26.0",
    "httpx>=0.27.0",
    "dill>=0.3.8",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=5.0.0",
    "ruff>=0.6.0",
]

[tool.ruff]
line-length = 88
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
ignore = ["E501"]

[tool.ruff.lint.isort]
known-first-party = ["src"]

[tool.pytest.ini_options]
minversion = "7.0"
addopts = "-ra -q --strict-markers"
testpaths = ["tests"]
pythonpath = ["src", "."]
```

- [ ] **Step 2: Criar `.graphifyignore` para exclusão de dados, modelos binários e logs**

```
# Datasets brutos e processados
data/raw/
data/processed/

# Modelos binários e artefatos pesados
models/*.pkl
models/history/

# Logs e execuções do Airflow
airflow_logs/
*.log

# Caches e artefatos de build
__pycache__/
*.pyc
.pytest_cache/
.ruff_cache/
.venv/
venv/
*.egg-info/
dist/
build/
.git/

# Saída do próprio graphify
graphify-out/
```

- [ ] **Step 3: Criar `.ai-jail` para controle de sandbox operacional**

```
# Sandbox configuration for AI Agents
SAFE_PATHS="src/,tests/,docs/,dags/,Makefile,pyproject.toml"
RESTRICTED_COMMANDS="rm -rf /,mkfs,dd,chmod 777"
NETWORK_ACCESS="local,pypi,github"
LOG_EXECUTION=true
```

- [ ] **Step 4: Executar verificação de lint com ruff**

Run: `uv run ruff check . || true`
Expected: Saída de verificação de arquivos python.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .graphifyignore .ai-jail
git commit -m "chore(harness): add pyproject.toml, .graphifyignore and .ai-jail configurations"
```

---

### Task 2: Makefile Operacional Completo

**Files:**
- Create: `Makefile`

- [ ] **Step 1: Criar `Makefile` com automação operacional e hooks**

```makefile
.PHONY: help dev run test test-cov lint format clean graphify setup-hooks pull-memory push-memory

PYTHON ?= python
UV ?= $(shell which uv 2>/dev/null || echo "uv")

help:
	@echo "UrgenSight - Harness de Desenvolvimento"
	@echo "----------------------------------------"
	@echo "make dev          - Sobe o ambiente local com docker-compose"
	@echo "make run          - Executa a API FastAPI localmente"
	@echo "make test         - Executa todos os testes unitarios e de integracao"
	@echo "make test-cov     - Executa testes com cobertura de codigo"
	@echo "make lint         - Executa analise estatica com Ruff"
	@echo "make format       - Formata codigo com Ruff"
	@echo "make clean        - Limpa caches e arquivos temporarios"
	@echo "make graphify     - Atualiza o Knowledge Graph do projeto"
	@echo "make setup-hooks  - Instala Git hooks de governanca e auto-staging"
	@echo "make pull-memory  - Sincroniza memorias locais com memorias da equipe"
	@echo "make push-memory  - Faz commit e publicacao de memorias da equipe"

dev:
	docker compose up -d --build

run:
	$(PYTHON) -m uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload

test:
	$(PYTHON) -m pytest

test-cov:
	$(PYTHON) -m pytest --cov=src --cov-report=term-missing

lint:
	$(PYTHON) -m ruff check src/ tests/ dags/

format:
	$(PYTHON) -m ruff format src/ tests/ dags/
	$(PYTHON) -m ruff check --fix src/ tests/ dags/

clean:
	rm -rf .pytest_cache .ruff_cache __pycache__ src/__pycache__ tests/__pycache__ dags/__pycache__ .coverage

graphify:
	@if command -v graphify >/dev/null 2>&1; then \
		graphify extract . -o graphify-out/; \
	else \
		echo "graphify nao instalado no PATH. Execute: uv tool install graphify-cli"; \
	fi

setup-hooks:
	@mkdir -p .git/hooks
	@echo '#!/bin/bash\n# Pre-commit hook: Auto-stage team memories and format check\nif [ -d ".gemini/memory/team" ]; then\n  git add .gemini/memory/team/ 2>/dev/null || true\nfi\nif [ -d ".claude/memory/team" ]; then\n  git add .claude/memory/team/ 2>/dev/null || true\nfi\nexit 0' > .git/hooks/pre-commit
	@chmod +x .git/hooks/pre-commit
	@echo "Git pre-commit hooks configurados com sucesso."

pull-memory:
	@if [ -f ".claude/sync-claude-memory.sh" ]; then bash .claude/sync-claude-memory.sh pull; fi
	@if [ -f ".gemini/sync-memory.sh" ]; then bash .gemini/sync-memory.sh pull; fi

push-memory:
	@if [ -f ".claude/sync-claude-memory.sh" ]; then bash .claude/sync-claude-memory.sh push; fi
	@if [ -f ".gemini/sync-memory.sh" ]; then bash .gemini/sync-memory.sh push; fi
```

- [ ] **Step 2: Testar execução do `make help` e `make setup-hooks`**

Run: `make help && make setup-hooks`
Expected: Menus exibidos e hook `.git/hooks/pre-commit` criado com permissão de execução.

- [ ] **Step 3: Commit**

```bash
git add Makefile
git commit -m "feat(harness): add operational Makefile with test, lint, format and hooks"
```

---

### Task 3: Instruções Paritárias (`CLAUDE.md` e `GEMINI.md`)

**Files:**
- Create: `CLAUDE.md`
- Create: `GEMINI.md`

- [ ] **Step 1: Criar `CLAUDE.md` (EN-US)**

```markdown
# UrgenSight - Engineering Agent Guidelines (Claude Code & OpenClaude)

UrgenSight is an automated medical text triage system (clinical notes classification into `normal`, `atencao`, `urgente`) built with FastAPI, Scikit-Learn, and Apache Airflow.

## 🛠️ Operational Commands (Makefile First)
Always prefer Makefile commands over raw shell commands:
- **Run Tests**: `make test`
- **Lint & Formatter**: `make lint` / `make format` (Ruff handles format & isort)
- **Local Dev Server**: `make run` (FastAPI at `http://localhost:8000`)
- **Knowledge Graph**: `make graphify` (Extracts/updates code graph)

## 📐 Architecture & Domain Conventions
- **Domain Flow**: Medical report text -> TF-IDF Vectorizer -> Logistic Regression / Linear SVC -> Class (`normal`, `atencao`, `urgente`).
- **FastAPI Lifespan**: Model loaded once at startup into `app.state.model`. If model is missing, API returns `503 Service Unavailable` with `{"detail": "Modelo de ML indisponivel."}`.
- **Airflow DAG**: `dags/train_pipeline.py` runs weekly with tasks: `load_and_validate_data -> train_model -> save_model`.
- **Environment Isolation**: `dill` and `scikit-learn==1.5.1` ensure serialized pickle compatibility between Airflow worker and FastAPI runtime.

## 🧠 Graph Engineering ("Graphify Before Grep/Glob")
Before performing raw grep/glob traversals across unfamiliar modules:
1. Consult the local knowledge graph in `graphify-out/` or run `graphify query <symbol>`.
2. Trace function dependencies and call chains deterministically.

## 🔒 Security & Governance Rules
- Never expose or commit sensitive data (`.env`, credentials, patient raw data).
- Keep tests isolated: never require active network or external database in unit tests.
- Maintain SemVer and update docs whenever API endpoints or schemas change.
```

- [ ] **Step 2: Criar `GEMINI.md` (pt-BR)**

```markdown
# UrgenSight - Diretrizes Operacionais (Gemini CLI / Antigravity)

O UrgenSight é um sistema inteligente de triagem de laudos médicos hospitalares desenvolvido em FastAPI, Scikit-Learn e Apache Airflow.

## ⚙️ Comandos de Execução Rápida
- **Testes Unitários e Integração**: `make test`
- **Verificação Estática e Lint**: `make lint`
- **Formatação Automática**: `make format`
- **Serviço FastAPI Local**: `make run`
- **Atualização do Grafo de Conhecimento**: `make graphify`
- **Sincronização de Memória**: `make pull-memory` / `make push-memory`

## 🏛️ Padrões de Arquitetura e ML
- **API**: Servida via FastAPI (`src/app.py`). O modelo é carregado no evento `lifespan`. Endpoints: `GET /health` e `POST /predict`.
- **Pipeline de Treino**: `src/prepare_dataset.py` e `src/train.py`.
- **DAG Airflow**: `dags/train_pipeline.py` orquestra retreino garantindo idempotência e versionamento em `models/history/`.
- **Compatibilidade de Pickle**: `scikit-learn==1.5.1` e `dill` fixados em `requirements.txt`.

## 🧭 Graph Engineering Compulsório
- Antes de varreduras extensivas de arquivos, utilize as consultas do Knowledge Graph (`graphify-out/`) para navegação determinística de símbolos e dependências.

## 👥 Memória Persistente de Equipe
- Diretório de memórias compartilhadas: `.gemini/memory/team/`.
- Registre decisões de arquitetura (ADRs) e regras de negócio validadas. Auto-staging habilitado via pre-commit hook.
```

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md GEMINI.md
git commit -m "docs(harness): add parity guidelines in CLAUDE.md and GEMINI.md"
```

---

### Task 4: Governança e Hooks do Eixo `.claude/`

**Files:**
- Create: `.claude/settings.json`
- Create: `.claude/protect-secrets.sh`
- Create: `.claude/verify-semver.sh`
- Create: `.claude/verify-docs.sh`
- Create: `.claude/sync-claude-memory.sh`
- Create: `.claude/memory/team/.gitkeep`

- [ ] **Step 1: Criar `.claude/settings.json` com hooks de ciclo de vida e zero-turn formatting**

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Read|Edit|Write",
        "command": "bash .claude/protect-secrets.sh \"$TOOL_INPUT_PATH\""
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "command": "if [[ \"$TOOL_INPUT_PATH\" == *.py ]]; then python -m ruff format \"$TOOL_INPUT_PATH\" 2>/dev/null && python -m ruff check --fix \"$TOOL_INPUT_PATH\" 2>/dev/null; fi"
      }
    ]
  }
}
```

- [ ] **Step 2: Criar `.claude/protect-secrets.sh` (com permissão `+x`)**

```bash
#!/bin/bash
# Pre-tool guard: Bloqueia leitura de arquivos com segredos sensíveis
TARGET_FILE="$1"

if [[ "$TARGET_FILE" =~ \.env($|\.) || "$TARGET_FILE" =~ credentials\.json || "$TARGET_FILE" =~ id_rsa || "$TARGET_FILE" =~ \.pem$ ]]; then
  echo "ERRO DE SEGURANÇA: Acesso a arquivo sensível bloqueado: $TARGET_FILE" >&2
  exit 1
fi

exit 0
```

- [ ] **Step 3: Criar `.claude/verify-semver.sh` (com permissão `+x`)**

```bash
#!/bin/bash
# Guard para checar compatibilidade de versão SemVer
VERSION=$(grep -E '^version\s*=' pyproject.toml | head -1 | cut -d'"' -f2)
if [[ -z "$VERSION" ]]; then
  echo "Aviso: Nenhuma versao SemVer encontrada em pyproject.toml"
  exit 0
fi
echo "UrgenSight SemVer: $VERSION"
exit 0
```

- [ ] **Step 4: Criar `.claude/verify-docs.sh` (com permissão `+x`)**

```bash
#!/bin/bash
# Guard para verificar se a documentacao essencial existe
REQUIRED_DOCS=("docs/api_contract.md" "docs/dataset.md" "docs/model_metrics.md" "README.md")

for doc in "${REQUIRED_DOCS[@]}"; do
  if [[ ! -f "$doc" ]]; then
    echo "Documento obrigatorio ausente: $doc" >&2
    exit 1
  fi
done
echo "Todos os documentos obrigatorios estao presentes."
exit 0
```

- [ ] **Step 5: Criar `.claude/sync-claude-memory.sh` (com permissão `+x`)**

```bash
#!/bin/bash
# Sincronizador de memorias da equipe
ACTION="${1:-pull}"
MEMORY_DIR=".claude/memory/team"

mkdir -p "$MEMORY_DIR"

case "$ACTION" in
  pull)
    echo "Memoria de equipe sincronizada em $MEMORY_DIR"
    ;;
  push)
    git add "$MEMORY_DIR" 2>/dev/null || true
    echo "Memorias de equipe preparadas para commit."
    ;;
  *)
    echo "Uso: $0 [pull|push]"
    exit 1
    ;;
esac
```

- [ ] **Step 6: Aplicar permissões executáveis e criar estrutura de diretórios**

Run: `chmod +x .claude/*.sh && mkdir -p .claude/memory/team && touch .claude/memory/team/.gitkeep`
Expected: Permissões atualizadas sem erros.

- [ ] **Step 7: Commit**

```bash
git add .claude/
git commit -m "feat(harness): add .claude settings, zero-turn ruff hooks and governance scripts"
```

---

### Task 5: Governança dos Eixos `.gemini/` e `.agents/`

**Files:**
- Create: `.gemini/settings.json`
- Create: `.gemini/sync-memory.sh`
- Create: `.gemini/memory/team/MEMORY.md`
- Create: `.agents/rules/core-skills.md`
- Create: `.agents/skills/.gitkeep`

- [ ] **Step 1: Criar `.gemini/settings.json`**

```json
{
  "hooks": {
    "AfterTool": [
      {
        "matcher": "Edit|Write",
        "command": "if [[ \"$TOOL_INPUT_PATH\" == *.py ]]; then python -m ruff format \"$TOOL_INPUT_PATH\" 2>/dev/null && python -m ruff check --fix \"$TOOL_INPUT_PATH\" 2>/dev/null; fi"
      }
    ]
  },
  "context": {
    "memoryPath": ".gemini/memory/team"
  }
}
```

- [ ] **Step 2: Criar `.gemini/sync-memory.sh` (com permissão `+x`)**

```bash
#!/bin/bash
# Sincronizador de memoria do Gemini CLI
ACTION="${1:-pull}"
MEMORY_DIR=".gemini/memory/team"

mkdir -p "$MEMORY_DIR"

case "$ACTION" in
  pull)
    echo "Memoria Gemini sincronizada em $MEMORY_DIR"
    ;;
  push)
    git add "$MEMORY_DIR" 2>/dev/null || true
    echo "Memorias Gemini preparadas para commit."
    ;;
  *)
    echo "Uso: $0 [pull|push]"
    exit 1
    ;;
esac
```

- [ ] **Step 3: Criar `.gemini/memory/team/MEMORY.md` inicial**

```markdown
# Memória Compartilhada de Equipe - UrgenSight

- [Arquitetura FastAPI](architecture-fastapi.md) — Modelo carregado no lifespan com fallback 503
- [Consistência de Pickle](pickle-compatibility.md) — Scikit-learn 1.5.1 e Dill obrigatórios
```

- [ ] **Step 4: Criar `.agents/rules/core-skills.md`**

```markdown
# Core Rules for AI Agents (UrgenSight)

1. **Deterministic Quality First**: Always run `make test` and `make lint` before declaring any task complete.
2. **Graphify Navigation**: Use knowledge graph queries to trace schemas, functions and call-sites before full-text codebase scans.
3. **Zero-Turn Formatting**: Code edits are automatically formatted by Ruff via post-tool hooks.
4. **Safety**: Never access, write, or leak credentials or raw medical data.
```

- [ ] **Step 5: Conceder permissões e commit**

Run: `chmod +x .gemini/*.sh && mkdir -p .agents/skills && touch .agents/skills/.gitkeep`
Expected: Permissões atualizadas.

- [ ] **Step 6: Commit**

```bash
git add .gemini/ .agents/
git commit -m "feat(harness): add .gemini and .agents governance configurations"
```

---

### Task 6: Subagentes Auditores e Skills Especializadas

**Files:**
- Create: `.claude/agents/ml-pipeline-verifier.md`
- Create: `.claude/agents/knowledge-graph-curator.md`
- Create: `.claude/skills/graphify/SKILL.md`
- Create: `.claude/skills/gen-api-test/SKILL.md`

- [ ] **Step 1: Criar Subagente `.claude/agents/ml-pipeline-verifier.md`**

```markdown
---
name: ml-pipeline-verifier
description: Subagente auditor para verificacao de integridade de modelos ML, pipelines e API FastAPI
---

# ML Pipeline Verifier Agent

Você é um agente auditor rigoroso com contexto zerado, especializado em integridade de Machine Learning e APIs clínicas.

## Suas Responsabilidades
1. **Auditoria de Contrato da API**:
   - Validar se `POST /predict` aceita `{"text": "..."}` e retorna `{"prediction": "normal|atencao|urgente"}`.
   - Validar se `GET /health` responde `200` com status quando o modelo está carregado e `503` quando ausente.
2. **Auditoria do Pipeline de Treino**:
   - Verificar se `src/prepare_dataset.py` e `src/train.py` mantêm tipos consistentes e serialização correta com `joblib`.
3. **Auditoria da DAG Airflow**:
   - Verificar se as 3 tasks (`load_and_validate_data -> train_model -> save_model`) mantêm idempotência e dependências sequenciais.

## Como Executar
Execute `make test` e inspecione as asserções de teste sem assumir resultados prévios.
```

- [ ] **Step 2: Criar Subagente `.claude/agents/knowledge-graph-curator.md`**

```markdown
---
name: knowledge-graph-curator
description: Subagente para curadoria e sincronizacao do Knowledge Graph
---

# Knowledge Graph Curator Agent

Você é o curador do Grafo de Conhecimento do repositório UrgenSight.

## Suas Responsabilidades
1. Manter as exclusões do `.graphifyignore` atualizadas.
2. Executar e validar a extração do grafo via `make graphify`.
3. Garantir que módulos recém-criados ou refatorados tenham suas dependências e nós mapeados.
```

- [ ] **Step 3: Criar Skill `.claude/skills/graphify/SKILL.md`**

```markdown
---
name: graphify
description: Executa consultas e navegacao no Knowledge Graph do UrgenSight
---

# Skill: graphify

Utilize esta skill para navegar de forma estruturada no grafo de conhecimento do código:

```bash
# Extrair ou atualizar o grafo
make graphify

# Consultar conexões de um símbolo
graphify query <nome_da_funcao_ou_classe>

# Explicar contexto do grafo
graphify explain <modulo>
```
```

- [ ] **Step 4: Criar Skill `.claude/skills/gen-api-test/SKILL.md`**

```markdown
---
name: gen-api-test
description: Gera testes automatizados padronizados para endpoints FastAPI usando httpx AsyncClient
---

# Skill: gen-api-test

Gera testes seguindo o padrão AAA (Arrange, Act, Assert) e usando o `test_client` assíncrono configurado no `tests/conftest.py`.
```

- [ ] **Step 5: Commit**

```bash
git add .claude/agents/ .claude/skills/
git commit -m "feat(harness): add specialized audit subagents and custom skills"
```

---

### Task 7: Modernização da Infraestrutura de Testes e Validação Completa

**Files:**
- Create: `tests/conftest.py`
- Modify: `tests/test_app.py` (garantir compatibilidade com fixtures globais)

- [ ] **Step 1: Criar `tests/conftest.py` com fixtures assíncronas e mock de ML**

```python
import os
import sys
from typing import AsyncGenerator
import pytest
from httpx import ASGITransport, AsyncClient

# Garante inclusão de src no sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from app import app


class DummyPipeline:
    """Mock determinístico para pipeline de Machine Learning nos testes."""

    def predict(self, texts):
        results = []
        for text in texts:
            t = text.lower()
            if "urgente" in t or "infarct" in t or "severe" in t:
                results.append("urgente")
            elif "atencao" in t or "moderate" in t:
                results.append("atencao")
            else:
                results.append("normal")
        return results


@pytest.fixture
def dummy_model():
    return DummyPipeline()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Cliente HTTP assíncrono para testes de integração rápidos na FastAPI."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
```

- [ ] **Step 2: Executar testes de validação completa via `make test`**

Run: `make test`
Expected: Todos os testes existentes e novos passando (PASS).

- [ ] **Step 3: Executar análise estática com `make lint` e `make format`**

Run: `make format && make lint`
Expected: Formatação e lint passando com zero erros.

- [ ] **Step 4: Validar scripts de governança**

Run: `bash .claude/verify-docs.sh && bash .claude/verify-semver.sh`
Expected: Validações concluídas com sucesso.

- [ ] **Step 5: Commit final**

```bash
git add tests/conftest.py
git commit -m "feat(tests): add pytest conftest with async test client and dummy model fixture"
```

---
