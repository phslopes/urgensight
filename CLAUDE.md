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
