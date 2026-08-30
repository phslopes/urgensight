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
