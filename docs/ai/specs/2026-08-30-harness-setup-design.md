# Design Doc: Implantação de Harness de Alta Maturidade (Nível 3) no UrgenSight

**Data**: 2026-08-30  
**Status**: Aprovado  
**Escopo**: Dual-Harness (OpenClaude / Claude Code & Gemini CLI / Antigravity)  
**Projeto**: UrgenSight (Sistema de Triagem Automática de Laudos Médicos - FastAPI / Scikit-Learn / Airflow / Docker)

---

## 1. Contexto e Objetivos

O projeto UrgenSight é composto por um pipeline de preparação de dados clínicos, treino e serialização de modelo de Machine Learning (`src/prepare_dataset.py`, `src/train.py`), orquestração periódica via Apache Airflow (`dags/train_pipeline.py`) e uma API de inferência de baixa latência em FastAPI (`src/app.py`).

O objetivo deste design é implantar a arquitetura completa de **Harness de Desenvolvimento Nível 3 (Maduro/Robusto)** conforme especificado em `docs/ai/guides/guia-construcao-harness.md`, garantindo paridade entre assistentes agênticos (Claude Code e Gemini CLI), automação de formatação zero-turn via Ruff, diretriz compulsória de Graph Engineering (`graphify`), subagentes auditores especializados com contexto zerado, sincronização bidirecional de memórias de equipe e infraestrutura de testes determinística.

---

## 2. Arquitetura em Três Eixos (Dual-Harness)

A governança e extensibilidade são organizadas em três eixos independentes e complementares:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 REPOSITÓRIO URGENSIGHT                                 │
├──────────────────────────┬─────────────────────────────┬───────────────────────────────┤
│         CLAUDE           │        COMPARTILHADO        │            GEMINI             │
├──────────────────────────┼─────────────────────────────┼───────────────────────────────┤
│ • .claude/               │ • .agents/                  │ • .gemini/                    │
│   ├── settings.json      │   ├── rules/core-skills.md  │   ├── settings.json           │
│   ├── skills/            │   └── skills/               │   ├── skills/                 │
│   ├── agents/            │ • Makefile                  │   ├── agents/                 │
│   ├── memory/            │ • pyproject.toml            │   ├── memory/team/            │
│   └── *.sh (Hooks/Guards)│ • .graphifyignore / .ai-jail│   └── sync-memory.sh          │
│ • CLAUDE.md              │                             │ • GEMINI.md                   │
└──────────────────────────┴─────────────────────────────┴───────────────────────────────┘
```

---

## 3. Especificação dos 7 Pilares

### Pilar 1: Instruções e Convenções Paritárias (`CLAUDE.md` / `GEMINI.md`)
- **`CLAUDE.md`** (EN-US): Foco em comandos práticos (`make *`), arquitetura da aplicação ML e rotas FastAPI, padrões de código, regras de versionamento SemVer e diretriz mandatória "Graphify Before Grep/Glob".
- **`GEMINI.md`** (pt-BR): Foco em workflows operacionais, MCP servers configurados, gestão de memórias persistentes de equipe em `.gemini/memory/team/`, ADRs e convenções de commit.

### Pilar 2: Formatação e Linting Zero-Turn (Hooks & Ruff)
- Configuração do linter/formatter `Ruff` em `pyproject.toml` (`line-length = 88`, `select = ["E", "F", "I", "UP"]`).
- Hooks de interceptação determinística em `.claude/settings.json` (`PostToolUse`) e `.gemini/settings.json` (`AfterTool`):
  - Ao editar qualquer arquivo `.py`, executa automaticamente `uv run ruff format && uv run ruff check --fix` de forma silenciosa (0 turnos de token desperdiçados com ajustes cosméticos).

### Pilar 3: Navegação Estruturada por Grafo (Graphify)
- Configuração do `.graphifyignore` para descartar datasets brutos/processados (`data/raw/`, `data/processed/`), artefatos binários (`models/*.pkl`), logs do Airflow (`airflow_logs/`), relatórios temporários e caches.
- Hooks de automação: `PostToolUse` / `AfterTool` acionam `graphify update .` em segundo plano quando arquivos de código ou documentação são modificados.
- Injeção obrigatória da diretiva *"Graphify Before Grep/Glob"* em subagentes e prompts de inicialização.

### Pilar 4: Taxonomia e Encadeamento de Skills
- Skills do framework Superpowers (`/brainstorming`, `/writing-plans`, `/subagent-driven-development`, `/verification`).
- Skills customizadas de projeto em `.claude/skills/` e `.gemini/skills/`:
  - `graphify`: Interface e comandos do grafo de conhecimento.
  - `gen-api-test`: Geração padronizada de testes de rotas FastAPI.
- Regras always-on centralizadas em `.agents/rules/core-skills.md`.

### Pilar 5: Subagentes Auditores Especializados (Contexto Zerado)
- **`ml-pipeline-verifier.md`** (`.claude/agents/` e `.gemini/agents/`): Subagente para auditoria defensiva de pipelines de Machine Learning, verificando schemas da FastAPI (`/predict`, `/health`), compatibilidade de serialização/desserialização de modelos e integridade das tasks do Airflow.
- **`knowledge-graph-curator.md`**: Subagente para manter e sincronizar o Knowledge Graph após alterações arquiteturais relevantes.

### Pilar 6: Memória Persistente e Git Pre-Commit Hook
- **Escopo Duplo**:
  - Memória Privada: `.claude/memory/` e `.gemini/memory/local/` (não versionada).
  - Memória de Equipe: `.gemini/memory/team/` e `.claude/memory/team/` (versionada no Git com ADRs, lições de incidentes e políticas de design).
- **Scripts de Sincronização**: `.claude/sync-claude-memory.sh` e `.gemini/sync-memory.sh`.
- **Git Hook**: Pre-commit hook configurado via `make setup-hooks` executando auto-staging transparente das memórias antes de finalizar o commit.

### Pilar 7: Infraestrutura de Testes & Isolamento em Memória
- Modernização de `tests/conftest.py` fornecendo fixtures assíncronas com `httpx.AsyncClient` e `ASGITransport` para FastAPI.
- Fixtures determinísticas para injeção de modelo dummy em testes unitários e de integração, garantindo que `pytest` execute em menos de 2 segundos de forma desacoplada de arquivos pesados em disco.

---

## 4. Plano de Arquivos a Criar e Atualizar

1. **Raiz**:
   - `CLAUDE.md` (novo)
   - `GEMINI.md` (novo)
   - `Makefile` (novo)
   - `pyproject.toml` (novo)
   - `.graphifyignore` (novo)
   - `.ai-jail` (novo)
2. **Eixo `.claude/`**:
   - `.claude/settings.json` (novo)
   - `.claude/protect-secrets.sh` (novo, executável)
   - `.claude/verify-semver.sh` (novo, executável)
   - `.claude/verify-docs.sh` (novo, executável)
   - `.claude/sync-claude-memory.sh` (novo, executável)
   - `.claude/agents/ml-pipeline-verifier.md` (novo)
   - `.claude/agents/knowledge-graph-curator.md` (novo)
   - `.claude/skills/graphify/SKILL.md` (novo)
   - `.claude/skills/gen-api-test/SKILL.md` (novo)
3. **Eixo `.gemini/`**:
   - `.gemini/settings.json` (novo)
   - `.gemini/sync-memory.sh` (novo, executável)
   - `.gemini/memory/team/.gitkeep` e memória inicial (novo)
4. **Eixo `.agents/`**:
   - `.agents/rules/core-skills.md` (novo)
   - `.agents/skills/.gitkeep` (novo)
5. **Suíte de Testes**:
   - `tests/conftest.py` (atualizado/criado)

---

## 5. Critérios de Aceite e Verificação

- [x] Arquivos `CLAUDE.md` e `GEMINI.md` implementados com paridade conceitual.
- [x] Comandos operacionais do `Makefile` (`make test`, `make lint`, `make format`) executando com sucesso via `uv`/`ruff`.
- [x] Scripts em `.claude/` e `.gemini/` criados com permissões de execução corretas (`chmod +x`).
- [x] Git pre-commit hook funcional e testado para auto-staging de memória.
- [x] Suíte de testes do repositório executando com 100% de sucesso através do `make test`.
