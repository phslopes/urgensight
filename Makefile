.PHONY: help dev run test test-cov lint format clean graphify setup-hooks pull-memory push-memory

UV ?= $(shell which uv 2>/dev/null)
ifeq ($(strip $(VIRTUAL_ENV)),)
  ifneq ($(strip $(UV)),)
    PYTHON ?= uv run python
  else
    PYTHON ?= python3
  endif
else
  PYTHON ?= python
endif

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
	@printf '#!/bin/bash\n# Pre-commit hook: Auto-stage team memories, protect secrets, verify semver\nif [ -d ".gemini/memory/team" ]; then\n  git add .gemini/memory/team/ 2>/dev/null || true\nfi\nif [ -d ".claude/memory/team" ]; then\n  git add .claude/memory/team/ 2>/dev/null || true\nfi\nbash .claude/scripts/protect-secrets.sh || exit 1\nbash .claude/scripts/verify-semver.sh || exit 1\nexit 0\n' > .git/hooks/pre-commit
	@chmod +x .git/hooks/pre-commit
	@echo "Git pre-commit hooks configurados com sucesso."

pull-memory:
	@if [ -f ".claude/sync-claude-memory.sh" ]; then bash .claude/sync-claude-memory.sh pull; fi
	@if [ -f ".gemini/sync-memory.sh" ]; then bash .gemini/sync-memory.sh pull; fi

push-memory:
	@if [ -f ".claude/sync-claude-memory.sh" ]; then bash .claude/sync-claude-memory.sh push; fi
	@if [ -f ".gemini/sync-memory.sh" ]; then bash .gemini/sync-memory.sh push; fi
