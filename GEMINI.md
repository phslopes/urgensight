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
- **Compatibilidade de Pickle**: `scikit-learn==1.5.1`, `numpy==1.26.4` e `dill` fixados em `pyproject.toml`/`uv.lock`.

## graphify

Rules for Autonomous Agent Exploration:

- **Graphify Before Grep/Glob**: MANDATORY: You MUST run `graphify query "<question>"` (or `graphify path` / `graphify explain`) for initial codebase exploration BEFORE executing any `Grep`, `Glob`, `grep_search`, or `search_file_content` tool calls. Only use raw search after graphify has oriented you.
- **Subagent Dispatch Directive**: When spawning or dispatching ANY subagent that involves codebase exploration, debugging, or architecture analysis, you MUST explicitly include the directive in the subagent's prompt forcing it to run `graphify` (`graphify query`, `graphify path`, or `graphify explain`) before any `Grep` or file search operations.
- **Autonomous Exploration**: ALWAYS use graphify internally during codebase explorations, architecture mapping, bug investigations, or feature planning. DO NOT wait for the user to explicitly type `/graphify` or request graphify commands manually.
- **Query First**: For any codebase or architecture question, run `graphify query "<question>"` when `graphify-out/graph.json` exists. Use `graphify path "<A>" "<B>"` for tracing relationships/dependencies and `graphify explain "<concept>"` for focused concepts.
- **Graph Updates**: After modifying code or if `graphify-out/graph.json` is missing/stale, run `graphify update .` automatically.

## 👥 Memória Persistente de Equipe

- Diretório de memórias compartilhadas: `.gemini/memory/team/`.
- Registre decisões de arquitetura (ADRs) e regras de negócio validadas. Auto-staging habilitado via pre-commit hook.

## 📝 Padrão de Commits

- Utilize rigorosamente o padrão **Conventional Commits em português (PT-BR)** (ex: `feat(api): ...`, `fix(modelo): ...`, `docs(ai): ...`, `chore(harness): ...`).
