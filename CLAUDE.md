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
- **Environment Isolation**: `numpy==1.26.4`, `pandas==2.1.4`, `dill`, and `scikit-learn==1.5.1` are pinned in `pyproject.toml`/`uv.lock` (installed via `uv sync`) to ensure serialized pickle compatibility between the Airflow worker and the FastAPI runtime.

## 🔒 Security & Governance Rules

## graphify

Rules for Autonomous Agent Exploration:

- **Graphify Before Grep/Glob**: MANDATORY: You MUST run `graphify query "<question>"` (or `graphify path` / `graphify explain`) for initial codebase exploration BEFORE executing any `Grep`, `Glob`, `grep_search`, or `search_file_content` tool calls. Only use raw search after graphify has oriented you.
- **Subagent Dispatch Directive**: When spawning or dispatching ANY subagent that involves codebase exploration, debugging, or architecture analysis, you MUST explicitly include the directive in the subagent's prompt forcing it to run `graphify` (`graphify query`, `graphify path`, or `graphify explain`) before any `Grep` or file search operations.
- **Autonomous Exploration**: ALWAYS use graphify internally during codebase explorations, architecture mapping, bug investigations, or feature planning. DO NOT wait for the user to explicitly type `/graphify` or request graphify commands manually.
- **Query First**: For any codebase or architecture question, run `graphify query "<question>"` when `graphify-out/graph.json` exists. Use `graphify path "<A>" "<B>"` for tracing relationships/dependencies and `graphify explain "<concept>"` for focused concepts.
- **Graph Updates**: After modifying code or if `graphify-out/graph.json` is missing/stale, run `graphify update .` automatically.

- Never expose or commit sensitive data (`.env`, credentials, patient raw data).
- Keep tests isolated: never require active network or external database in unit tests.
- Maintain SemVer and update docs whenever API endpoints or schemas change.
- **Commit Messages Standard**: Always write commit messages following **Conventional Commits in Brazilian Portuguese (PT-BR)** (e.g., `feat(api): adicionar endpoint`, `fix(pipeline): corrigir preprocessamento`, `docs(ai): atualizar plano`).
