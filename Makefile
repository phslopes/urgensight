.PHONY: help dev ensure-model dev-airflow run train test test-cov lint format clean graphify setup-hooks pull-memory push-memory load monitoring-down

# uv e obrigatorio (ADR-0007): o fallback anterior para o interpretador do
# sistema permitia que cada integrante rodasse num ambiente diferente.
UV := $(shell command -v uv 2>/dev/null)
ifeq ($(strip $(UV)),)
  $(error uv nao encontrado no PATH. Instale com: curl -LsSf https://astral.sh/uv/install.sh | sh)
endif
PYTHON := uv run python

help:
	@echo "UrgenSight - Harness de Desenvolvimento"
	@echo "----------------------------------------"
	@echo "make dev          - Sobe a stack de monitoramento (API + Prometheus + Grafana)"
	@echo "make dev-airflow  - Sobe a stack do Airflow (docker-compose.airflow.yml)"
	@echo "make monitoring-down - Derruba a stack de monitoramento"
	@echo "make load         - Gera carga de requisicoes contra a API local"
	@echo "make run          - Executa a API FastAPI localmente"
	@echo "make test         - Executa todos os testes unitarios e de integracao"
	@echo "make test-cov     - Executa testes com cobertura de codigo"
	@echo "make lint         - Executa analise estatica com Ruff"
	@echo "make format       - Formata codigo com Ruff"
	@echo "make clean        - Limpa caches e arquivos temporarios"
	@echo "make train        - Prepara dataset e treina o modelo (gera models/model.pkl)"
	@echo "make graphify     - Atualiza o Knowledge Graph do projeto"
	@echo "make setup-hooks  - Instala Git hooks de governanca e auto-staging"
	@echo "make pull-memory  - Sincroniza memorias locais com memorias da equipe"
	@echo "make push-memory  - Faz commit e publicacao de memorias da equipe"

train:
	$(PYTHON) -m src.prepare_dataset
	$(PYTHON) -m src.train

dev: ensure-model
	docker compose up -d --build
	@echo "API:        http://localhost:8000/docs"
	@echo "Prometheus: http://localhost:9090/targets"
	@echo "Grafana:    http://localhost:3000"

ensure-model:
	@if [ ! -f models/model.pkl ]; then \
		echo "models/model.pkl ausente -- executando make train..."; \
		$(MAKE) train; \
	fi

dev-airflow:
	docker compose -f docker-compose.airflow.yml up -d --build

monitoring-down:
	docker compose down

load:
	$(PYTHON) scripts/generate_load.py

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
	@printf '#!/bin/bash\nset -euo pipefail\n# Pre-commit hook: Auto-stage team memories, sync memory, protect secrets, verify semver\nif [ -d ".gemini/memory/team" ]; then\n  git add .gemini/memory/team/ 2>/dev/null || true\nfi\nif [ -d ".claude/memory/team" ]; then\n  git add .claude/memory/team/ 2>/dev/null || true\nfi\nmake pull-memory >/dev/null 2>&1 || true\nbash .claude/scripts/protect-secrets.sh || exit 1\nbash .claude/scripts/verify-semver.sh || exit 1\nexit 0\n' > .git/hooks/pre-commit
	@printf '#!/bin/bash\nset -euo pipefail\n# Post-commit hook: sync memory back to the shared stores\nmake push-memory >/dev/null 2>&1 || true\nexit 0\n' > .git/hooks/post-commit
	@chmod +x .git/hooks/pre-commit .git/hooks/post-commit
	@echo "Git hooks configurados com sucesso."

pull-memory:
	@if [ -f ".claude/sync-claude-memory.sh" ]; then bash .claude/sync-claude-memory.sh pull; fi
	@if [ -f ".gemini/sync-memory.sh" ]; then bash .gemini/sync-memory.sh pull; fi

push-memory:
	@if [ -f ".claude/sync-claude-memory.sh" ]; then bash .claude/sync-claude-memory.sh push; fi
	@if [ -f ".gemini/sync-memory.sh" ]; then bash .gemini/sync-memory.sh push; fi
