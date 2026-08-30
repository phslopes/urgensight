<!--
  LOG DE MANUTENÇÃO:
  - 2026-08-24: Adicionada regra proibindo tamanhos arbitrários de texto em pixels no Tailwind (ex: text-[10px]); uso obrigatório da escala nativa.
  - 2026-08-24: Adicionada diretriz obrigatória de identificação e gestão de sessões via /color e /rename.
-->

# 🚀 Guia Prático de Construção e Operação de Harness de Alta Maturidade para Agentes de IA

**Data**: 06 de Agosto de 2026
**Versão**: 1.1.0
**Status**: Aprovado / Guia Operacional
**Escopo**: Dual-Harness (OpenClaude / Claude Code & Gemini CLI)
**Autor**: Equipe de Engenharia de IA & Arquitetura de Sistemas

---

## ⚙️ Seção 0: Pré-Requisitos e Setup Inicial

> 💡 **Leia antes de começar.** Esta seção deve ser executada uma única vez em cada máquina de desenvolvimento. Ela garante que todas as ferramentas do Harness estejam instaladas e configuradas antes de qualquer interação com agentes de IA.

---

### 0.1 Ferramentas Obrigatórias

| Ferramenta | Propósito no Harness | Instalação |
| :--- | :--- | :--- |
| `make` (GNU Make) | Automação de atalhos operacionais, setup de hooks e sandbox | Pré-instalado ou `brew install make` / `apt install make` |
| `uv` | Gerenciador de pacotes Python (substitui pip/poetry) | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| `ruff` | Linter e formatter Python (zero-turn via hooks) | Instalado via `uv` no `pyproject.toml` |
| `graphify` | Navegação por Knowledge Graph (compulsória) | `pip install graphify-cli` ou `uv tool install graphify-cli` |
| `docker` + `docker-compose` | Ambiente de dev isolado (MySQL + API) | [docs.docker.com/get-docker](https://docs.docker.com/get-docker/) |
| `jq` | Parsing de JSON nos hooks de ciclo de vida | `brew install jq` (macOS) / `apt install jq` (Linux) |
| `ai-jail` *(opcional)* | Sandbox de segurança para isolar os agentes | `make jail-setup` (ver seção 0.4) |
| OpenClaude / Claude Code CLI | Agente de IA principal (harness Claude) | [claude.ai/code](https://claude.ai/code) |
| Gemini CLI | Agente de IA auxiliar (harness Gemini) | `npm install -g @google/gemini-cli` |

---

### 0.2 Variáveis de Ambiente

O ecossistema de agentes (MCPs, Stitch, GitHub) requer tokens de acesso carregados no shell. O repositório possui um script dedicado para isso:

```bash
# 1. Copiar e preencher o arquivo de ambiente
make env

# 2. Carregar as variáveis no shell atual
source scripts/load-env.sh

# 3. Verificar se as variáveis estão disponíveis
make export-env
```

**Variáveis críticas que devem estar presentes no `.env`:**

| Variável | Uso |
| :--- | :--- |
| `GITHUB_PERSONAL_ACCESS_TOKEN` | MCP GitHub (criação de PRs, issues) |
| `STITCH_API_KEY` | MCP Stitch (Google UI design) |
| `FIGMA_TOKEN` | MCP Figma (design assets) |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Autenticação OAuth2 da API |
| `DATABASE_URL` | Conexão com MySQL local/Docker |

---

### 0.3 Quick Start: Setup do Harness em 10 Passos (Novo Repositório)

Execute os comandos abaixo em sequência ao clonar o repositório pela primeira vez ou ao configurar um novo projeto para garantir que todo o ecossistema do agente esteja funcional:

```bash
# 1. Instalar dependências Python
uv sync

# 2. Carregar variáveis de ambiente (Tokens MCPs e BD)
make env
source scripts/load-env.sh

# 3. Subir o ambiente de desenvolvimento (Docker)
make dev
# A API estará disponível em http://localhost:8000

# 4. Verificar infraestrutura de testes em memória
make test

# 5. Gerar o Knowledge Graph inicial (OBRIGATÓRIO antes de usar agentes)
graphify extract . --force --code-only
# O grafo base será gerado em graphify-out/graph.json

# 6. Instalar o Git pre-commit hook (auto-staging de memória e validações)
make setup-gemini-hook

# 7. Sincronizar memória global do agente para o repositório local
make pull-memory

# 8. (Opcional) Instalar o sandbox de segurança AI Jail
make jail-setup

# 9. Testar conexão do Agente e MCPs no Sandbox
make jail-gemini
# No prompt do Gemini, digite: /mcp-status para verificar se o GitHub e Stitch MCP estão online

# 10. Realizar o commit inicial de setup
git add .
git commit -m "chore(harness): setup inicial do dual-harness, graphify e hooks"
# O pre-commit hook (Passo 6) validará Ruff, testes rápidos e sincronizará a memória
```

---

### 0.4 Setup do AI Jail (Sandbox — Opcional mas Recomendado)

O `ai-jail` isola os agentes de IA em um sandbox controlado, prevenindo acesso acidental a diretórios sensíveis fora do repositório:

```bash
# Instalar e configurar o ai-jail
make jail-setup

# Rodar OpenClaude isolado no sandbox
make jail-openclaude

# Rodar Gemini CLI isolado no sandbox
make jail-gemini
```

A configuração de isolamento do projeto está em [`.ai-jail`](.ai-jail) na raiz do repositório.

---

### 0.5 Sincronização de Memória entre Máquinas

Quando um desenvolvedor inicia em uma nova máquina ou após um clone fresh, o repositório local não possui as memórias acumuladas dos agentes. Para sincronizar:

```bash
# Puxar memórias do repositório para o sistema local (~/.gemini e ~/.claude)
make pull-memory

# Enviar memórias locais de volta ao repositório (após o agente criar novas)
make push-memory
```

O hook de pre-commit (`make setup-gemini-hook`) executa `pull-memory` automaticamente a cada commit, garantindo que o repositório sempre reflita o estado mais atual das memórias.

---

## 📖 Introdução e Visão Geral

À medida que o desenvolvimento orientado a agentes de IA evolui da geração simples de trechos de código para a engenharia autônoma de sistemas inteiros, a infraestrutura que envolve e apoia o agente torna-se tão crítica quanto o próprio modelo de linguagem. Essa infraestrutura de suporte, governança, validação e execução é chamada de **Harness de Desenvolvimento para Agentes de IA**.

Sem um Harness estruturado, o agente opera em um ambiente sem balizas: sofre de desvio de contexto (context drift), comete erros de estilo recorrentes que consomem múltiplos turnos de correção, gera alucinações arquiteturais, entra em loops de lint e invalida o histórico da janela de contexto com buscas brutas ineficientes.

### 📊 Níveis de Maturidade do Harness

A capacidade e confiabilidade do Harness de um repositório são classificadas em 3 níveis de maturidade:

1. **Nível 1 (Incipiente)**: Operação reativa do agente sem guardrails automatizados. Prompts manuais repetitivos, sem hooks de formatação zero-turn, buscas brutas via `Grep`/`Glob`, sem gestão de memória persistente e testes executados contra banco de dados físico local ou ausentes.
2. **Nível 2 (Intermediário)**: Convenções de projeto alinhadas (`CLAUDE.md`), hooks básicos de lint e scripts isolados de teste. Contudo, ainda padece de perda de contexto entre sessões, falta de orquestração de skills e buscas textuais custosas em bases de código grandes.
3. **Nível 3 (Maduro / Robusto - Target deste Guia)**: Estado da arte em engenharia de agentes. Apresenta paridade **Dual-Harness** (`CLAUDE.md` ↔ `GEMINI.md`), automação zero-turn de formatação (`Ruff`), navegação relacional compulsória por grafo de conhecimento (`Graphify`), orquestração encadeada de skills, subagentes auditores isolados, memória persistente com auto-staging no Git e suíte de testes em memória determinística (`SQLite async` + `conftest.py`).

Com uma estrutura de **Nível 3 (Maduro / Robusto)**, o Harness transforma o agente em um engenheiro de software de alta precisão. Ele fornece:

- **Execuções Determinísticas**: Regras arquiteturais injetadas e aplicadas compulsoriamente sem necessidade de repetição manual nos prompts.
- **Automação Zero-Turn**: Hooks de ciclo de vida que formatam e validam o código silenciosamente em tempo real antes e depois do uso das ferramentas.
- **Eficiência Extrema de Tokens**: Economia comprovada em produção de **~42.7% no consumo total de tokens**, alcançada substituindo buscas textuais cegas por navegação estruturada via grafo de conhecimento (`Graphify`) e eliminando turnos de correção de formatação.
- **Isolamento e Segurança**: Subagentes auditores com janela de contexto limpa e testes executados inteiramente em memória sem poluir o banco de dados de desenvolvimento.

---

## ☯️ Filosofia Dual-Harness (OpenClaude / Claude Code + Gemini CLI)

Projetos modernos de grande porte frequentemente utilizam múltiplos assistentes e CLIs de IA em um ecossistema multiplataforma. Este guia adota a **Filosofia Dual-Harness (Três Eixos)**, garantindo paridade funcional e simetria absoluta entre o **OpenClaude / Claude Code CLI** e o **Gemini CLI / Antigravity** no mesmo repositório de código, através de um diretório compartilhado (`.agents/`).

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 REPOSITÓRIO DE CÓDIGO                                  │
├──────────────────────────┬─────────────────────────────┬───────────────────────────────┤
│         CLAUDE           │        COMPARTILHADO        │            GEMINI             │
├──────────────────────────┼─────────────────────────────┼───────────────────────────────┤
│ • .claude/               │ • .agents/                  │ • .gemini/                    │
│   ├── settings.json      │   ├── rules/core-skills.md  │   ├── settings.json           │
│   ├── skills/            │   ├── skills/               │   ├── skills/                 │
│   ├── agents/            │   ├── workflows/            │   ├── agents/                 │
│   ├── memory/            │   └── plugins/              │   └── memory/                 │
│   └── *.sh (Hooks)       │                             │   └── sync-memory.sh          │
│                          │ • Makefile (targets)        │                               │
│ • CLAUDE.md              │ • .ai-jail / .graphifyignore│ • GEMINI.md                   │
└──────────────────────────┴─────────────────────────────┴───────────────────────────────┘
```

A coexistência harmoniosa entre ambos os assistentes é garantida por:

1. **Paridade de Instruções**: O arquivo `CLAUDE.md` e o `GEMINI.md` compartilham a mesma paridade conceitual de regras de arquitetura (DDD, Vertical Slice), diretrizes de linguagem (documentação em pt-BR, commits em EN-US) e convenções de código.
2. **Camada Compartilhada (`.agents/`)**: Regras always-on (`core-skills.md`), workflows operacionais e a biblioteca principal de skills (marketplace/genéricas) vivem no `.agents/` para não serem duplicadas.
3. **Sincronização Cruzada de Memória**: O diretório `.gemini/memory/` e a estrutura `.claude/memory/team/` contêm decisões de equipe e padrões, protegidos de serem esquecidos por auto-staging no pre-commit hook.
4. **Respeito aos Guardrails**: Ambos os assistentes obedecem à mesma filosofia de exploração compulsória por grafo (`graphify`), isolamento em sandbox (`ai-jail`) e execução de scripts de validação (`Makefile` e hooks).

---

## 🏛️ Seção 1: Os 7 Pilares do Harness de Alta Maturidade

Um Harness de Nível 3 é sustentado por sete pilares fundamentais de engenharia, cada um responsável por resolver um gargalo específico na interação entre o agente e a codebase.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                          OS 7 PILARES DO HARNESS DE NÍVEL 3                            │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  [Pilar 1] Instruções Paritárias ──► CLAUDE.md e GEMINI.md com convenções vivas       │
│  [Pilar 2] Formatação Zero-Turn ───► Hooks Pre/Post Tool Use (Ruff format & lint)      │
│  [Pilar 3] Partida Compulsória  ───► Diretriz "Graphify Before Grep/Glob"              │
│  [Pilar 4] Taxonomia de Skills  ───► Superpowers + Matt Pocock + Skills de Domínio     │
│  [Pilar 5] Subagentes Isolados  ───► Auditores dedicados (migration-verifier)         │
│  [Pilar 6] Memória & Git Hooks  ───► Auto-staging de memórias via pre-commit           │
│  [Pilar 7] Testes em Memória    ───► conftest.py async + SQLite in-memory determinístico │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

### 1.1 Pilar 1: Instruções e Convenções Paritárias (`CLAUDE.md` / `GEMINI.md`)

O primeiro pilar consiste em centralizar a inteligência e o contexto arquitetural da codebase em arquivos de configuração que são carregados automaticamente no início de cada sessão.

- **Eliminação de Poluição de Prompt**: Em vez de repetir comandos de build, regras de commit ou padrões de pasta em cada requisição do usuário, o Harness injeta essas regras na raiz do projeto (`CLAUDE.md` e `GEMINI.md`).
- **Arquitetura Vertical Slice & DDD**: Define explicitamente que cada módulo do projeto (ex: `src/app/{modulo}/`) é uma fatia vertical contendo seus próprios `models.py`, `schemas.py`, `repository.py`, `service.py`, `use_cases.py` e `router.py`.
- **Política Rígida de Idioma**:
  - **Português do Brasil (pt-BR)**: Toda a documentação técnica, planos de execução (`specs`/`plans`), relatórios, ADRs e comentários explicativos.
  - **Inglês (EN-US)**: Todo o código fonte, identificadores, nomes de variáveis e mensagens de commit no padrão **Conventional Commits** (`<type>(<scope>): <subject>`).
- **Paridade Total**: Alterações de regras arquiteturais devem ser replicadas simultaneamente em `CLAUDE.md` e `GEMINI.md` para evitar divergência comportamental entre assistentes.

---

### 1.2 Pilar 2: Automações e Formatação Zero-Turn (Hooks)

O segundo pilar aborda a eliminação de turnos desnecessários de conversação (token waste) através da interceptação silenciosa no ciclo de vida das ferramentas.

- **O Problema da Correção Reativa**: Sem hooks automatizados, quando o agente edita um arquivo Python e viola uma regra de estilo (ex: PEP 8, ordenação de imports), o linter falha no pipeline de CI ou o usuário precisa solicitar manualmente "Rode o linter e corrija". Isso consome de 2 a 4 turnos de conversa e dezenas de milhares de tokens.
- **A Solução Zero-Turn**: O Harness utiliza hooks registrados no `.claude/settings.json` (ou scripts de interceptação equivalente):
  - **Hook `PreToolUse` / `PostToolUse`**: Sempre que a ferramenta `Edit` ou `Write` modifica um arquivo `.py`, o Harness executa automaticamente o comando `make format && make lint` (`Ruff`).
  - **Interceptação Transparente**: O código é ajustado, formatado e higienizado antes mesmo de retornar o controle ao agente ou ao usuário, garantindo 0 turnos gastos com ajustes superficiais de sintaxe.

---

### 1.3 Pilar 3: Ponto de Partida Compulsório (Graphify & Knowledge Graph)

O terceiro pilar transforma a forma como o agente navega pela codebase, substituindo a busca cega por palavras-chave por exploração relacional contextualizada.

- **Diretriz "Graphify Before Grep/Glob"**: O Harness estabelece uma regra mandatória: antes de executar qualquer busca por texto bruto via `Grep` ou varredura via `Glob`, o agente é obrigado a consultar o Grafo de Conhecimento (`graphify-out/graph.json`) através do comando `graphify query "<pergunta>"`, `graphify explain "<conceito>"` ou `graphify path "<A>" "<B>"`.
- **Economia de Tokens e Visão Holística**: O grafo abstrai nós de comunidade, dependências entre módulos, fluxos de chamadas e entidades críticas. Em vez de ler dezenas de arquivos inteiros para entender como um módulo funciona, o agente recebe o subgrafo exato com suas conexões.
- **Injeção Compulsória em Subagentes**: Qualquer subagente disparado pelo agente principal herda compulsoriamente a diretiva de consultar o Graphify como primeira ação de exploração.

---

### 1.4 Pilar 4: Orquestração e Taxonomia de Skills

O quarto pilar organiza as habilidades estendidas (Skills) do agente em uma taxonomia clara por origem e responsabilidade, permitindo seu encadeamento fluido durante o desenvolvimento.

1. **Skills do Framework Superpowers (`superpowers:*`)**:
   - *Proveniência*: Plugin oficial Superpowers.
   - *Foco*: Governança e execução do ciclo de vida da tarefa.
   - *Exemplos*: `/brainstorming`, `/writing-plans`, `/subagent-driven-development`, `/executing-plans`, `/verification`.
2. **Skills do Agentic Engineering / Matt Pocock (`agentic-engineering:*`)**:
   - *Proveniência*: Padrões de engenharia de agentes de Matt Pocock.
   - *Foco*: Desafio técnico e validação adversária de design.
   - *Exemplos*: `/grill-me`, `/test-driven-development`, `/refactoring`.
3. **Skills Customizadas Claude (`.claude/skills/`)**:
   - *Proveniência*: Desenvolvidas sob medida, versionadas no repositório.
   - *Foco*: Automações locais específicas do Claude Code CLI.
   - *Skills disponíveis*: `create-migration` (migrations Alembic defensivas), `gen-route-test` (testes FastAPI), `graphify` (extração do grafo), `fullstack-cost-git-report` (relatórios de métricas).
4. **Skills Compartilhadas Gemini/Antigravity (`.agents/skills/` e `.gemini/skills/`)**:
   - *Proveniência*: Instaladas via marketplace ou versionadas para o Gemini CLI / Antigravity.
   - *Foco*: Capacidades genéricas (design, debugging, segurança, auditoria) e padrões específicos do projeto.
   - *Skills do `.agents/skills/`*: `api-endpoint-builder`, `bug-hunter`, `brooks-lint`, `logic-lens`, `performance-optimizer`, `k6-load-testing`, `codebase-audit-pre-push`, entre outras.
   - *Skills do `.gemini/skills/`*: `achieving-100-percent-coverage`, `bulk-saving-pattern`, `domain-first-test-structure`, `api-route-trailing-slash-normalization`, entre outras.

---

### 1.5 Pilar 5: Subagentes de Verificação com Contexto Isolado

O quinto pilar desacopla tarefas de auditoria complexas do processo principal, prevenindo a poluição do histórico de conversação (context bloat).

- **Janela de Contexto Limpa**: Quando o agente principal realiza uma alteração estrutural profunda (como criar uma migração de banco de dados ou refatorar um repositório), disparar auditorias dentro da mesma conversa sobrecarrega o histórico e induz alucinações.
- **Subagentes Especializados do Projeto**: O Harness define dois subagentes isolados, versionados em `.claude/agents/` e `.gemini/agents/`:
  - **`migration-verifier`**: Audita arquivos de migração Alembic, verificando idempotência, DDL defensivo (`has_table`/`has_column`), funções `upgrade()`/`downgrade()` simétricas e import no `models_registry`. Retorna `[APROVADO / REJEITADO]` com pontos de atenção.
  - **`knowledge-graph-curator`**: Respónsavel por inspecionar e reorganizar o grafo de conhecimento (`graphify-out/`) após refatorações estruturais grandes. Garante que nós orphãos sejam removidos e que a wiki do grafo (`graphify-out/wiki/`) esteja atualizada.

---

### 1.6 Pilar 6: Memória Persistente e Estratégia de Git Hooks

O sexto pilar garante que os aprendizados, decisões arquiteturais e incidentes superados pelo agente sejam salvos permanentemente e compartilhados entre toda a equipe de desenvolvimento.

- **Escopo Duplo de Memória**:
  - **Memória Privada**: Armazena preferências locais do desenvolvedor, configurações de ambiente e histórico pessoal. Localizada em `.claude/memory/` (arquivos não prefixados com `team`) e apenas local.
  - **Memória de Equipe**: Armazena decisões arquiteturais (ADRs), registros de bugs históricos, padrões de teste de rotas, convenções de schema e políticas de migração. Localizada em `.claude/memory/team/` (mais de 56 arquivos no projeto atual) e `.gemini/memory/`.
- **Automação via Git Pre-Commit Hooks**:
  - O comando `make setup-gemini-hook` instala o hook em `.git/hooks/pre-commit`.
  - **Auto-Staging Transparente**: O hook executa `.claude/sync-claude-memory.sh pull`, que usa `rsync` para atualizar `.claude/memory/` a partir do diretório global do assistente e faz `git add` automaticamente.

---

### 1.7 Pilar 7: Infraestrutura de Testes & Isolation em Memória

> 💡 **Nota de Referência**: Para as diretrizes e convenções detalhadas de escrita de testes (padrão AAA, nomenclatura e estratégias de mock), consulte o diretório de guias [Padrões de Escrita de Testes](docs/guides/testing/test-writing-standards.md).

O sétimo pilar fornece um ambiente de execução de testes rápido, determinístico e isolado de efeitos colaterais.

- **SQLite Async In-Memory**: As suítes de teste de integração de rotas FastAPI utilizam o SQLite em memória (`sqlite+aiosqlite:///:memory:`), configurado no arquivo `tests/conftest.py`. Isso permite criar e destruir o esquema completo do banco em milissegundos sem depender de instâncias externas de MySQL/PostgreSQL para testes rápidos.
- **Isolamento de Dependências com FastAPI `dependency_overrides`**: O Harness impõe a substituição do Unit of Work (`get_uow`) pelas fixtures do `conftest.py`.
- **Limpeza Obrigatória em Blocos `finally`**: Todos os testes e utilitários limpam explicitamente o dicionário de overrides (`app.dependency_overrides.clear()`) para prevenir contaminação de estado entre casos de teste distintos.

---

## 🔄 2. O Ciclo de Vida do Agente & Workflow Cruzado

O desenvolvimento autônomo e assistido por IA opera através de um fluxo estruturado em **5 Fases Interconectadas**. Cada fase aciona artefatos específicos do Harness, garantindo que o agente navegue do entendimento do problema à persistência do resultado sem desvio de contexto, sem regressões de estilo e sem desperdício de tokens.

### 2.1 Visão Geral do Ciclo de Vida em 5 Fases

O diagrama abaixo ilustra a transição contínua entre as fases e o mapeamento com os componentes do Harness:

#### Diagrama Mermaid

```mermaid
flowchart TD
    subgraph F1["Fase 1: Bootstrapping & Context Loading"]
        A1["Carregamento Passivo<br/>(CLAUDE.md / GEMINI.md)"] --> A2["Leitura de Memórias<br/>(MEMORY.md & team/)"]
        A2 --> A3["Exploração Compulsória<br/>(graphify query)"]
    end

    subgraph F2["Fase 2: Análise, Design & Sabatina"]
        B1["Brainstorming & Specs<br/>(/brainstorming)"] --> B2["Sabatina Adversária<br/>(/grill-me)"]
        B2 --> B3["Plano Cirúrgico<br/>(/writing-plans)"]
    end

    subgraph F3["Fase 3: Execução & Edit Zero-Turn"]
        C1["Leitura Direcionada via Grafo"] --> C2["Edição de Código<br/>(Edit / Write)"]
        C2 --> C3["Hooks Pre/Post Tool Use<br/>(Ruff format & lint)"]
    end

    subgraph F4["Fase 4: Auditoria & Verificação Independente"]
        D1["Subagente com Contexto Zerado<br/>(migration-verifier / verification)"] --> D2["Suíte de Testes em Memória<br/>(conftest.py + SQLite in-memory)"]
    end

    subgraph F5["Fase 5: Persistência & Manutenção do Harness"]
        E1["Atualização Silenciosa do Grafo<br/>(graphify update .)"] --> E2["Persistência de Aprendizados<br/>(Private & Team Memories)"]
        E2 --> E3["Auto-Staging de Memória no Git<br/>(make setup-gemini-hook / /memory-sync-setup)"]
    end

    F1 --> F2
    F2 --> F3
    F3 --> F4
    F4 --> F5
```

#### Fluxo ASCII Estruturado

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│ FASE 1: BOOTSTRAPPING & CONTEXT LOADING                                          │
│ ├─► Leitura passiva compulsória de CLAUDE.md / GEMINI.md                         │
│ ├─► Carregamento automático de MEMORY.md e memórias de equipe (.gemini/memory/)   │
│ └─► Execução OBRIGATÓRIA do Graphify Query (graphify query) antes de Grep/Glob   │
├──────────────────────────────────────────────────────────────────────────────────┤
│ FASE 2: ANÁLISE, DESIGN & SABATINA                                               │
│ ├─► Invocação da skill /brainstorming para especificação iterativa               │
│ ├─► Execução proativa e encadeada do /grill-me (sabatina adversária de design)   │
│ └─► Transição para /writing-plans (decomposição cirúrgica de tarefas)           │
├──────────────────────────────────────────────────────────────────────────────────┤
│ FASE 3: EXECUÇÃO & EDIT ZERO-TURN                                                │
│ ├─► Leitura direcionada de arquivos identificados no Grafo de Conhecimento       │
│ ├─► Chamada da ferramenta Edit / Write                                           │
│ └─► Interceptação Hooks PreToolUse/PostToolUse: make format && make lint (Ruff)  │
├──────────────────────────────────────────────────────────────────────────────────┤
│ FASE 4: AUDITORIA & VERIFICAÇÃO INDEPENDENTE                                     │
│ ├─► Disparo de subagente secundário com contexto zerado (migration-verifier)     │
│ └─► Execução de testes em memória (conftest.py + SQLite assíncrono in-memory)   │
├──────────────────────────────────────────────────────────────────────────────────┤
│ FASE 5: PERSISTÊNCIA & MANUTENÇÃO DO HARNESS                                     │
│ ├─► Atualização silenciosa incremental do grafo (graphify update .)              │
│ ├─► Registro de memórias aprendidas na sessão (Privadas e de Equipe)             │
│ └─► Git Pre-Commit Hook (make setup-gemini-hook): auto-staging de memórias       │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

### 2.2 Mapeamento Cruzado Detalhado das 5 Fases

#### 1. Fase 1: Bootstrapping & Context Loading

No início de qualquer sessão, o Harness força o alinhamento arquitetural do agente antes do envio da primeira mensagem do usuário ou do primeiro comando.

- **Leitura Passiva e Compulsória de Instruções**: O agente consome os arquivos `CLAUDE.md` e `GEMINI.md`, incorporando as regras do projeto (DDD Vertical Slice, política de linguagem pt-BR/EN-US, padrões de commit e linter).
- **Carregamento Automático de Memórias**: O histórico acumulado no `MEMORY.md` e em `.gemini/memory/team/` é injetado no contexto, garantindo que incidentes anteriores, decisões de design (ADRs) e convenções vigentes sejam imediatamente conhecidos.
- **Partida Compulsória por Grafo (`graphify query`)**: Antes de realizar qualquer busca genérica por arquivos ou strings brutas, o agente obrigatoriamente consulta o Grafo de Conhecimento (`graphify query "<pergunta>"`). Isso orienta a navegação reduzindo a varredura desnecessária de diretórios em até 90%.

#### 2. Fase 2: Análise, Design & Sabatina

Antes de escrever qualquer linha de código produtivo, a demanda passa pelo pipeline de validação de design.

- **Refinamento Iterativo via `/brainstorming`**: A skill de especificação orienta a criação do spec técnico em `docs/ai/specs/`, definindo requisitos, arquitetura afetada e critérios de aceite.
- **Sabatina Adversária com `/grill-me`**: O agente dispara proativamente o `/grill-me` para estressar o design proposto. A sabatina questiona premissas, riscos de segurança, gargalos de performance, falhas em schemas Pydantic/SQLAlchemy e compatibilidade de migrações.
- **Decomposição em Plano Cirúrgico via `/writing-plans`**: Com o spec aprovado e sabatinado, o plano de execução é gerado em `docs/ai/plans/`, dividindo a tarefa em etapas granulares e testáveis sob a perspectiva de TDD.

#### 3. Fase 3: Execução & Edit Zero-Turn

A fase de modificação de código é protegida por automações que impedem a contaminação do histórico de conversação com erros superficiais de estilo.

- **Leitura Direcionada de Código**: O agente lê exclusivamente os arquivos apontados pelas consultas ao grafo e pelo plano de execução.
- **Modificação via Ferramentas Rígidas (`Edit` / `Write`)**: O agente altera os arquivos necessários aplicando o mínimo de código viável e reutilizando abstrações já existentes na codebase.
- **Interceptação Zero-Turn via Hooks (`PreToolUse` / `PostToolUse`)**: Assim que a ferramenta de edição é executada, os hooks configurados em `.claude/settings.json` disparam silenciosamente `make format && make lint` (`Ruff`). Qualquer desvio de formatação, import não utilizado ou violação de estilo é corrigido automaticamente pelo ambiente sem gastar turnos do modelo de linguagem ou tokens de feedback.

#### 4. Fase 4: Auditoria & Verificação Independente

A validação das alterações é isolada do contexto principal para garantir imparcialidade e prevenir alucinações.

- **Disparo de Subagentes com Contexto Zerado**: Para alterações críticas (como migrações Alembic ou refatorações de segurança), um subagente especializado (ex: `migration-verifier`) é spawnado com uma janela de contexto limpa. O subagente inspeciona o diff de forma autônoma e emite um parecer sintético.
- **Execução de Testes Determinísticos em Memória**: A suíte de testes de integração é executada utilizando as fixtures de `tests/conftest.py`, rodando sobre SQLite assíncrono em memória. Os testes validam as rotas FastAPI e contratos Pydantic sem afetar o banco de dados de desenvolvimento.

#### 5. Fase 5: Persistência & Manutenção do Harness

Após a conclusão da tarefa, o estado do repositório e a memória do agente são sincronizados para sessões futuras.

- **Atualização Incremental do Grafo de Conhecimento**: O hook `PostToolUse` dispara o comando `graphify update .` em background, atualizando os nós, arestas e subgrafos modificados durante a edição.
- **Persistência de Aprendizados (`MEMORY.md`)**: Novos padrões arquiteturais ou soluções de bugs descobertos na sessão são documentados no diretório de memórias (dividos entre escopo privado e de equipe).
- **Auto-Staging de Memória no Git**: O script Git pre-commit hook (configurado via `make setup-gemini-hook` e `/memory-sync-setup`) intercepta o comando de commit e adiciona automaticamente os arquivos de memória atualizados (`.gemini/memory/` e `.openclaude/.../memory/`) ao staging do Git, garantindo que o conhecimento permaneça versionado e sincronizado com o time.

---

## 🕸️ 3. Ponto de Partida Compulsório: Graphify & Knowledge Graph

> 💡 **Nota de Referência**: Para o detalhamento completo de arquitetura, instalação, comandos e integração avançada do Graphify, consulte o [Guia de Integração e Operação de Graph Engineering](docs/guides/guia-integracao-graph-engineering.md).

Em repositórios de médio e grande porte, a forma como o agente de IA navega pela estrutura de arquivos determina diretamente a eficiência de tokens, o tempo de resposta e a taxa de acerto nas implementações. O **Graphify** atua como o motor de navegação estruturada do Harness, substituindo a busca cega por texto bruto por consultas relacionais em um Grafo de Conhecimento (Knowledge Graph).

---

### 3.1 A Diretriz "Graphify Before Grep/Glob"

#### 1. Fundamentação Técnica e Ineficiência da Busca Textual Pura

Quando um agente utiliza ferramentas de busca por texto bruto (`Grep`) ou varredura de arquivos (`Glob`) no início de uma investigação, dois problemas graves ocorrem:

- **Alucinação de Escopo & Falsos Positivos**: A busca textual retorna ocorrências em arquivos de teste, fixtures, documentação obsoleta, variáveis locais ou logs, levando o agente a concluir incorretamente como o código opera ou a editar o arquivo errado.
- **Desperdício de Janela de Contexto (Token Waste)**: O agente lê múltiplos arquivos inteiros para mapear mentalmente dependências que poderiam ser compreendidas em uma única estrutura hierárquica. Em projetos reais, isso consome dezenas de milhares de tokens por turno.

#### 2. Extração de Topologia via AST (Abstract Syntax Tree)

O `graphify` resolve essa limitação analisando a árvore de sintaxe abstrata (AST) do código fonte e gerando um mapa relacional detalhado mantido em `graphify-out/graph.json`. Ele identifica automaticamente:

- **God Nodes**: Módulos ou classes centrais com alto grau de acoplamento e múltiplas dependências de entrada/saída (ex: `UnitOfWorkImpl`, `AbstractBaseRepository`).
- **Hierarquia de Comunidades**: Agrupamentos lógicos de componentes que colaboram estreitamente dentro de cada fatia vertical do domínio.
- **Relacionamentos Cross-File**: Mapeamento preciso de chamadas de funções, heranças de classes, importações de schemas DTO e injeções de dependência entre camadas.

#### 3. Comandos Fundamentais e Invocação Prática

| Comando                           | Escopo e Objetivo                                                                                         | Exemplo de Invocação                                                |
| :-------------------------------- | :-------------------------------------------------------------------------------------------------------- | :-------------------------------------------------------------------- |
| `graphify query "<pergunta>"`   | Busca contextual que retorna o subgrafo relevante focado na pergunta solicitada.                          | `graphify query "como funciona a autenticação OTP e JWT?"`        |
| `graphify path "<A>" "<B>"`     | Mapeia o caminho completo de dependências e chamadas entre dois nós ou componentes.                     | `graphify path "src/app/auth/router.py" "src/core/unit_of_work.py"` |
| `graphify explain "<conceito>"` | Fornece uma explicação focada nas abstrações, entidades de domínio e fluxos de dados de um conceito. | `graphify explain "politica de autorizacao abac"`                   |

---

### 3.2 Mecanismo de Hook-Guards de Interceptação

Para garantir que a diretriz de busca relacional seja respeitada deterministicamente pelo agente (e não apenas uma sugestão ignorada), o Harness utiliza um mecanismo de **Hook-Guards de Interceptação**.

1. **Interceptação no `PreToolUse`**:
   Sempre que o agente tenta disparar as ferramentas `Read`, `Grep` ou `Glob` para exploração de código, o evento `PreToolUse` intercepta a requisição e valida a existência do grafo em `graphify-out/graph.json`.
2. **Bloqueio Educativo via `system-reminder`**:
   Caso o agente tente realizar buscas puras sem ter consultado o Grafo de Conhecimento previamente, o sistema injeta um alerta contextual mandatório:

   ```
   PreToolUse:Read hook additional context: MANDATORY: graphify-out/graph.json exists. 
   You MUST run graphify before reading source files. Use: `graphify query "<question>"`, 
   `graphify explain "<concept>"`, or `graphify path "<A>" "<B>"`. 
   Only read raw files after graphify has oriented you, or to modify/debug specific lines.
   ```

   Este bloqueio força o agente a recuar, executar o `graphify query` e orientar sua busca apenas nos arquivos realmente relevantes identificados pelo subgrafo.

---

### 3.3 Diretiva Obrigatoriamente Injetada em Subagentes (Subagent Dispatch Directive)

Uma das maiores causas de desvio em arquiteturas multi-agente ocorre quando o agente principal é disciplinado, mas os subagentes que ele dispara voltam a usar `Grep`/`Glob` descontroladamente.

#### A Regra de Ouro da Injeção de Prompts

Sempre que o agente principal instanciar ou despachar qualquer subagente (via ferramenta `Agent` ou criação de prompts de subagentes), é **estritamente obrigatório** incluir a **Subagent Dispatch Directive** no prompt de inicialização do subagente.

#### Cláusula de Injeção Pronta para Uso em Prompts de Orquestração:

```markdown
### 🚨 MANDATORY DIRECTIVE FOR CODE EXPLORATION
You MUST run graphify (`graphify query "<question>"`, `graphify path "<A>" "<B>"`, 
or `graphify explain "<concept>"`) to orient yourself within the codebase architecture 
BEFORE invoking any `Grep` or `Glob` tool calls. Only use `Grep` or `Glob` after `graphify` 
has oriented you or when searching for exact literal code strings during edits.
```

Esta cláusula garante que o isolamento do subagente mantenha os mesmos padrões de eficiência de tokens e precisão do agente principal.

---

### 3.4 Sincronização Incremental Silenciosa & Manutenção do Grafo

O Grafo de Conhecimento só é útil se refletir o estado real e atualizado da codebase. O Harness automatiza a manutenção do grafo sem interromper o fluxo de trabalho do desenvolvedor ou do agente.

#### 1. Automação Incremental no `PostToolUse`

Após qualquer edição de código realizada pelas ferramentas `Edit` ou `Write`, o hook de `PostToolUse` dispara silenciosamente em segundo plano:

```bash
graphify update .
```

Este comando analisa apenas os arquivos modificados na sessão e atualiza incrementalmente os nós e arestas afetados no `graphify-out/graph.json`, sem a necessidade de reindexar todo o repositório.

#### 2. Reindexação Limpa em Mudanças no `.graphifyignore`

Quando novas regras de exclusão ou padrões de ignore são adicionados ao arquivo `.graphifyignore` (ex: ignorar pastas de relatórios temporários, diretórios de logs ou builds), o grafo local deve ser purificado para remover nós obsoletos. O Harness executa:

```bash
graphify extract . --force --code-only
```

Este comando força um escaneamento limpo e reconstrução integral do grafo focando exclusivamente no código-fonte, garantindo que arquivos descartados não poluam a visualização da arquitetura.

---

## ⚡ 4. Taxonomia e Orquestração Encadeada de Skills

As extensões de capacidade (Skills) expandem as habilidades nativas do agente de IA, fornecendo procedimentos padronizados, atalhos operacionais e fluxos metodológicos. Para evitar superposição de responsabilidades e garantir a máxima qualidade no código gerado, o Harness organiza as skills em uma **taxonomia de três origens lógicas**, permitindo seu encadeamento orquestrado durante todas as fases do ciclo de desenvolvimento.

---

### 4.1 Taxonomia de Origens e Responsabilidades

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                          TAXONOMIA DE SKILLS NO HARNESS                                │
├────────────────────────────┬────────────────────────────┬──────────────────────────────┤
│ 1. FRAMEWORK SUPERPOWERS   │ 2. MATT POCOCK / AGENTIC   │ 3. SKILLS DE DOMÍNIO         │
│    (superpowers:*)         │    (agentic-engineering:*) │    (.claude/skills/)         │
├────────────────────────────┼────────────────────────────┼──────────────────────────────┤
│ • Processo & Rigor         │ • Validação Adversária     │ • Automação Local & DDLs     │
│ • /brainstorming           │ • /grill-me                │ • /create-migration          │
│ • /writing-plans           │ • /test-driven-development │ • /gen-route-test            │
│ • /subagent-driven-dev     │ • /refactoring             │ • /graphify                  │
│ • /systematic-debugging    │                            │ • /fullstack-cost-git-report │
│ • /executing-plans         │                            │                              │
│ • /verification            │                            │                              │
└────────────────────────────┴────────────────────────────┴──────────────────────────────┘
```

#### 1. Framework Superpowers (`superpowers:*`)

- **Origem e Propósito**: Plugin oficial Anthropic/Claude Code projetado para impor rigor metodológico, orquestração de subagentes isolados e controle estrito sobre o fluxo de desenvolvimento.
- **Principais Skills**: `/brainstorming`, `/writing-plans`, `/subagent-driven-development`, `/systematic-debugging`, `/executing-plans`, `/verification`.
- **Papel no Harness**: Atuar como a espinha dorsal de governança e execução. Garante que nenhuma linha de código seja produzida sem especificação e plano, e que a execução ocorra tarefa a tarefa por subagentes com contexto isolado (`/subagent-driven-development`).

#### 2. Matt Pocock / Agentic Engineering (`agentic-engineering:*`)

- **Origem e Propósito**: Padrões táticos e técnicas avançadas de engenharia de agentes desenvolvidos por Matt Pocock para estressar soluções, sabatinar premissas e aumentar a precisão técnica.
- **Principais Skills**: `/grill-me`, `/test-driven-development`, `/refactoring`.
- **Papel no Harness**: Prover validação adversária intensiva do design. Destaca-se o uso do `/grill-me` para sabatinar o agente, identificando falhas de premissa, vulnerabilidades de segurança e riscos arquiteturais antes da fase de implementação.

#### 3. Skills Customizadas de Domínio / Projeto (`.claude/skills/`)

- **Origem e Propósito**: Skills desenvolvidas sob medida e versionadas no próprio repositório para automatizar tarefas específicas da arquitetura do projeto MonFinTrack.
- **Principais Skills**: `/create-migration`, `/gen-route-test`, `/graphify`, `/fullstack-cost-git-report`.
- **Papel no Harness**: Encodar regras de negócio locais e padrões de infraestrutura. Automatiza a geração de migrações DDL Alembic defensivas, criação de testes de integração com isolamento no `conftest.py`, extração do grafo de conhecimento e geração de relatórios de métricas.

---

### 4.2 Grafo de Encadeamento de Skills e Transições-Chave

O verdadeiro poder do Harness reside na capacidade de encadear skills de origens distintas em um pipeline contínuo, onde o output de uma skill alimenta compulsoriamente a entrada da próxima.

#### Diagrama Mermaid de Encadeamento Inter-Skills

```mermaid
flowchart TD
    subgraph S1["Fase de Design & Especificação"]
        A["/brainstorming<br/>(Superpowers)"] -->|"Sabatina Obrigatória"| B["/grill-me<br/>(Matt Pocock)"]
        B -->|"Aprovação do Spec"| C["/writing-plans<br/>(Superpowers)"]
    end

    subgraph S2["Fase de Execução & Arquitetura"]
        C -->|"Plano Decomposto"| D["/subagent-driven-development<br/>(Superpowers)"]
        D -->|"Demanda DDL Banco"| E["/create-migration<br/>(Domínio)"]
        D -->|"Demanda Nova Rota"| F["/gen-route-test<br/>(Domínio)"]
    end

    subgraph S3["Fase de Verificação & Testes"]
        E -->|"DDL Gerada"| G["migration-verifier<br/>(Subagente)"]
        F -->|"Teste Gerado"| H["conftest.py / SQLite async<br/>(Suíte de Testes)"]
        G & H --> I["/verification<br/>(Superpowers)"]
    end

    subgraph S4["Fase de Fechamento & Grafo"]
        I -->|"Sucesso"| J["/graphify<br/>(Domínio)"]
        J --> K["Commit & Auto-Staging<br/>(Git Hooks)"]
    end
```

#### Tabela de Transições-Chave entre Skills

| Origem ➔ Destino                                                                | Transição de Contexto           | Descrição do Fluxo e Benefício                                                                                                                                                                                          |
| :------------------------------------------------------------------------------- | :-------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`/brainstorming` (Superpowers) ➔ `/grill-me` (Matt Pocock)**        | Design ➔ Sabatina Adversária    | A skill de brainstorming aciona obrigatoriamente a sabatina do `/grill-me` para encontrar falhas no design, riscos de segurança e gargalos de performance antes de consolidar o documento de especificação (`spec`). |
| **`/brainstorming` ➔ `/writing-plans` (Superpowers)**                 | Spec Aprovado ➔ Plano Cirúrgico | Transição direta após a aprovação do spec, onde o problema é decomposto em passos granulares e sequenciais de implementação em `docs/ai/plans/`.                                                                  |
| **`/writing-plans` ➔ `/subagent-driven-development` (Superpowers)**   | Plano ➔ Delegação Paralela     | O plano cirúrgico é executado através de subagentes isolados para cada tarefa, mantendo a janela de contexto limpa e isolada para cada modificação.                                                                   |
| **`/create-migration` (Domínio) ➔ `migration-verifier` (Subagente)** | DDL ➔ Auditoria em Background    | A skill de domínio gera a migração Alembic defensiva (checando `has_table`/`has_column`) e dispara o subagente auditor em background com contexto zerado para validação.                                           |
| **`/gen-route-test` (Domínio) ➔ `conftest.py` (Suíte de Testes)**   | Rota FastAPI ➔ Isolamento SQLite | A skill gera os testes de rotas acoplados às fixtures assíncronas do `conftest.py`, aplicando `dependency_overrides` no `get_uow` com SQLite in-memory determinístico.                                             |

---

## 🧠 5. Memória Persistente, Estratégias de Git Hooks e Dual-Harness

À medida que um repositório evolui e múltiplos agentes e desenvolvedores interagem com a codebase, o conhecimento sobre decisões arquiteturais, bugs superados, refinamentos de esquema e convenções de teste não pode ficar restrito a janelas de contexto temporárias ou à memória volátil do modelo de linguagem. A infraestrutura do Harness deve garantir a **persistência determinística de memória** e a **sincronização automática entre o time** via versionamento no Git.

---

### 5.1 Escopo Duplo de Memória: Privada vs. Equipe

O Harness divide o armazenamento de conhecimento em dois escopos lógicos fundamentais com propósitos e níveis de compartilhamento distintos:

#### 1. Memória Privada (`private`)

- **Propósito**: Registrar preferências individuais do desenvolvedor, estilo de comunicação, atalhos de ambiente, configurações personalizadas de IDE/CLI e atalhos operacionais locais.
- **Localização**: `.openclaude/projects/.../memory/` (específico por projeto/usuário) ou `.gemini/memory/local/`.
- **Compartilhamento**: Exclusiva do ambiente local do desenvolvedor; não deve ser commitada em repositórios públicos ou compartilhada globalmente para evitar contaminação do fluxo de trabalho dos demais membros do time.

#### 2. Memória de Equipe (`team`)

- **Propósito**: Armazenar o conhecimento arquitetural compartilhado, decisões de design (ADRs), lições aprendidas em incidentes de produção, regras rígidas de banco de dados (ex: migrações defensivas), políticas de isolamento de testes e convenções de rotas FastAPI.
- **Localização**: `.gemini/memory/team/` ou `.openclaude/.../memory/team/`.
- **Compartilhamento**: Versionada no repositório Git e compartilhada entre todos os desenvolvedores e assistentes de IA da organização.

#### 3. Estrutura de Arquivos de Memória e Formato Frontmatter

Para que o agente consiga indexar e consultar memórias com máxima eficiência, todos os arquivos de memória no Harness devem seguir um padrão rígido de cabeçalho YAML (frontmatter) e estrutura de corpo dividida em três seções mandatórias.

##### Exemplo de Arquivo de Memória (`.gemini/memory/team/policy_migration_defensiva.md`):

````markdown
---
name: policy_migration_defensiva
description: Exigência de validação defensiva com has_table e has_column em migrações Alembic
type: team
---

### Regra / Fato
Toda migração de banco de dados gerada via Alembic deve obrigatoriamente validar a existência prévia de tabelas e colunas antes de executar operações de DDL (`op.create_table`, `op.add_column`, `op.drop_column`).

### Motivo (Why)
Em ambientes de produção e staging, migrações anteriores podem ter sido aplicadas parcialmente ou esquemas de banco podem divergir ligeiramente. Executar DDLs cegas sem verificações defensivas pode resultar em falhas catastróficas de migração em produção (conforme registrado no Incidente de Julho de 2026).

### Como Aplicar (How to apply)
Utilizar a skill `/create-migration` ou inspecionar o objeto `op.get_bind()` com `sa.inspect()`. Exemplo:
```python
bind = op.get_bind()
inspector = sa.inspect(bind)
if not inspector.has_table("minha_tabela"):
    op.create_table(...)
```
````

---

### 5.2 Automação via Git Pre-Commit Hooks e Comandos do OpenClaude

A persistência de memória em um repositório distribuído corre o risco de falhar se depender da ação manual do desenvolvedor para adicionar (`git add`) os arquivos de memória atualizados pelo agente ao commit. O Harness resolve esse problema através da automação de Git Hooks.

#### 1. Instalação e Execução via `make setup-gemini-hook`

O comando de infraestrutura `make setup-gemini-hook` configura o script Bash no `.git/hooks/pre-commit` do repositório. O fluxo de execução do hook atua em duas frentes:

- **Validação & Formatação de Código**: Dispara `make format && make lint` (`Ruff`) para garantir zero desvios de código.
- **Auto-Staging Transparente de Memórias**: O hook varre os diretórios de memória (`.gemini/memory/` e `.openclaude/.../memory/`) em busca de modificações não estagiadas ou novos arquivos criados durante a sessão do agente e executa compulsoriamente `git add` nesses arquivos antes que o commit seja finalizado.

#### 2. Comando Nativo OpenClaude `/memory-sync-setup`

O OpenClaude fornece o comando nativo `/memory-sync-setup`, responsável por vincular o repositório local à memória global do assistente. Ao ser executado, ele:

- Registra os ganchos de sincronização de memória no arquivo de configuração do repositório.
- Garante que alterações feitas em memórias globais durante a sessão do assistente sejam imediatamente espelhadas na pasta de memórias do projeto local.
- Habilita o rastreamento automático de diffs nas memórias compartilhadas do time.

#### 3. Fluxo Sequencial de Auto-Staging de Memórias

```mermaid
sequenceDiagram
    autonumber
    participant Dev as Agente / Desenvolvedor
    participant Mem as Pasta de Memórias (.gemini/memory/team/)
    participant Git as Git Client (git commit)
    participant Hook as Pre-Commit Hook (make setup-gemini-hook)
    participant Repo as Repositório Git Local

    Dev->>Mem: Atualiza ou cria memória (ex: policy_new_rule.md)
    Dev->>Git: Executa `git commit -m "feat: new feature"`
    Git->>Hook: Intercepta commit (Pre-Commit Hook Trigger)
    Hook->>Hook: Executa `make format && make lint`
    Hook->>Mem: Verifica alterações em `.gemini/memory/` e `.openclaude/`
    Hook->>Git: Executa `git add .gemini/memory/ .openclaude/` (Auto-Staging)
    Hook->>Repo: Permite que o commit prossiga com o código E as memórias
    Repo-->>Dev: Commit realizado com sucesso (Código + Memórias sincronizadas)
```

---

### 5.3 Estratégia Dual-Harness (OpenClaude / Claude Code + Gemini CLI)

Projetos enterprise se beneficiam do uso complementar de múltiplos assistentes de IA (ex: OpenClaude / Claude Code para refinamento cirúrgico de código e agentes locais; Gemini CLI / Antigravity para auditorias de contexto longo e análises de grande escala). Para que múltiplos assistentes trabalhem no mesmo código sem conflitos, o Harness aplica a **Estratégia Dual-Harness**.

#### 1. Garantia de Paridade Funcional Absoluta

Nenhum assistente deve ter privilégios de conhecimento ou regras exclusivas que faltem ao outro. Se o OpenClaude exige o uso do Graphify ou a política de linguagem em pt-BR/EN-US, o Gemini CLI deve possuir compulsoriamente o mesmo alinhamento.

#### 2. Alinhamento Paritário de Instrução: `CLAUDE.md` ↔ `GEMINI.md`

O Harness mantém dois arquivos centrais de instruções na raiz do projeto com paridade conceitual (não textual):

- `CLAUDE.md`: Lido nativamente pelo OpenClaude / Claude Code CLI (inglês, foco em código).
- `GEMINI.md`: Lido nativamente pelo Gemini CLI / Antigravity (pt-BR, foco em workflows e MCPs).
- Ambos os arquivos compartilham a mesma definição da arquitetura Vertical Slice (DDD), as mesmas regras de Alembic (`models_registry.py`), a mesma exigência da diretriz "Graphify Before Grep/Glob" e o mesmo conjunto de scripts (`make dev`, `make test`, `make lint`, `make pull-memory`).

#### 3. Coexistência Limpa de Configurações (Três Eixos)

O repositório mantém **três eixos de configuração** com responsabilidades distintas:

```
┌──────────────────────────────────────────────────────────────────────┐
│                    REPOSITÓRIO DE CÓDIGO                              │
├─────────────────────┬──────────────────────┬─────────────────────────┤
│ .claude/            │ .gemini/             │ .agents/                │
├─────────────────────┼──────────────────────┼─────────────────────────┤
│ settings.json       │ settings.json        │ rules/core-skills.md   │
│ (Hooks Claude)      │ (Hooks+MCPs Gemini)  │ (regras always-on)      │
│                     │                      │                         │
│ skills/             │ skills/              │ skills/                 │
│ (Claude-specific)   │ (Gemini-specific)    │ (marketplace/genéricas) │
│                     │                      │                         │
│ agents/             │ agents/              │ workflows/              │
│ (Subagentes Claude) │ (Subagentes Gemini)  │ (audit, performance...) │
│                     │                      │                         │
│ memory/             │ memory/              │ plugins/                │
│ (Memória OpenClaude)│ (Memória Gemini)     │ (marketplace.json)      │
│                     │                      │                         │
│ protect-secrets.sh  │ sync-memory.sh       │                         │
│ verify-semver.sh    │                      │                         │
│ verify-docs.sh      │                      │                         │
│ sync-claude-mem.sh  │                      │                         │
└─────────────────────┴──────────────────────┴─────────────────────────┘
```

- **`.claude/`**: Configuração exclusiva do Claude Code CLI — hooks de segurança, governança e formatação, skills locais específicas, subagentes Claude, memória local do OpenClaude e scripts de sincronização.
- **`.gemini/`**: Configuração exclusiva do Gemini CLI — hooks `BeforeTool`/`AfterTool`, 7 servidores MCP configurados, skills específicas de padrões do projeto, subagente knowledge-graph-curator e memória do Gemini.
- **`.agents/`**: Configuração **compartilhada** entre ambos os assistentes — rules always-on (`core-skills.md`), biblioteca de 35+ skills genéricas (marketplace), 3 workflows operacionais (audit, performance, ui-polish) e plugins marketplace.

Ambos os ambientes compartilham os mesmos recursos do sistema (`make setup-gemini-hook`, o grafo em `graphify-out/`, e o `Makefile`), garantindo interoperabilidade sem conflitos no controle de versão.

---


## 📜 6. Blueprints e Modelos de Artefatos Prontos para Cópia

Nesta seção são disponibilizados 6 blueprints operacionais completos, testados e prontos para serem copiados diretamente para o seu repositório.

---

### 6.1 Blueprint 1: Configuração de Hooks JSON em `.claude/settings.json`

O arquivo `.claude/settings.json` define a interceptação determinística de ferramentas (`PreToolUse` e `PostToolUse`). O harness real opera com **quatro blocos de hooks** distintos: proteção de secrets, governança de release, guardrail do Graphify e formatação/lint automático.

> 📌 **Nota de Formato**: Os matchers usam strings separadas por pipe (`|`) e os hooks são objetos aninhados dentro de um array `hooks`. Este formato difere de exemplos simplificados de outros guias.

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Read|Write|Edit|Grep",
        "hooks": [
          {
            "type": "command",
            "command": "for d in . .openclaude .claude .. ../.claude ../.openclaude; do [ -f \"$d/protect-secrets.sh\" ] && exec bash \"$d/protect-secrets.sh\"; done; exit 0"
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "bash .claude/verify-semver.sh"
          },
          {
            "type": "command",
            "command": "bash .claude/verify-docs.sh"
          }
        ]
      },
      {
        "matcher": "Bash|Grep",
        "hooks": [
          {
            "type": "command",
            "command": "/Users/<SEU_USER>/.local/bin/graphify hook-guard search"
          }
        ]
      },
      {
        "matcher": "Read|Glob",
        "hooks": [
          {
            "type": "command",
            "command": "/Users/<SEU_USER>/.local/bin/graphify hook-guard read"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "(jq -r '.tool_response.filePath // .tool_input.file_path' | grep -E '\\.py$' && make format && make lint) || true",
            "statusMessage": "Formatando e corrigindo lint com Ruff..."
          }
        ]
      },
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "FILE=$(jq -r \".tool_response.filePath // .tool_input.file_path\"); if echo \"$FILE\" | grep -q \"\\.graphifyignore$\"; then /Users/<SEU_USER>/.local/bin/graphify extract . --force --code-only; elif echo \"$FILE\" | grep -qE \"\\.(py|md)$\"; then /Users/<SEU_USER>/.local/bin/graphify update .; fi || true",
            "statusMessage": "Atualizando grafo de conhecimento com Graphify..."
          }
        ]
      }
    ]
  }
}
```

> ⚠️ **Substituição Obrigatória**: Substitua `/Users/<SEU_USER>/` pelo caminho real do seu usuário. Para encontrar o path correto do graphify: `which graphify`.

---

#### Scripts de Governança do Harness (`.claude/`)

Além do `settings.json`, o diretório `.claude/` contém scripts Bash que são invocados pelos hooks acima. Eles devem ser criados na raiz de `.claude/` e ter permissão de execução (`chmod +x`):

**`.claude/protect-secrets.sh`** — Bloqueia leitura de arquivos sensíveis:

```bash
#!/bin/bash
input=$(cat)
file_path=$(echo "$input" | jq -r '.tool_input.file_path // .tool_input.filePath // .tool_input.path // empty' 2>/dev/null)

if [ -n "$file_path" ]; then
  if echo "$file_path" | grep -v "protect-secrets" | grep -q -i -E '\.env|/secrets/|key\.pem$|id_rsa$'; then
    echo '{"continue": false, "stopReason": "Acesso bloqueado em arquivos confidenciais (.env, secrets, chaves)."}'
    exit 0
  fi
fi

if echo "$input" | grep -v "protect-secrets" | grep -q -i -E '"(file_path|filePath|path)":\s*"[^"]*(\\.env|/secrets/|key\.pem|id_rsa)'; then
  echo '{"continue": false, "stopReason": "Acesso bloqueado em arquivos confidenciais (.env, secrets, chaves)."}'
  exit 0
fi

exit 0
```

**`.claude/verify-semver.sh`** — Bloqueia merge/push sem bump de versão no `pyproject.toml`:

```bash
#!/bin/bash
COMMAND=$(jq -r '.tool_input.command' 2>/dev/null)

if echo "$COMMAND" | grep -qE "git merge|git push.*main|git push.*develop" && [ -f "pyproject.toml" ]; then
    VERSION_LOCAL=$(grep -E "^version =" pyproject.toml | head -n 1 | cut -d'"' -f2)
    VERSION_MAIN=$(git show origin/main:pyproject.toml 2>/dev/null | grep -E "^version =" | head -n 1 | cut -d'"' -f2)

    if [ -n "$VERSION_LOCAL" ] && [ -n "$VERSION_MAIN" ] && [ "$VERSION_LOCAL" = "$VERSION_MAIN" ]; then
        MSG="⚠️ [BLOQUEIO SEMVER] A versão local ($VERSION_LOCAL) é idêntica à main. Atualize o SemVer antes do merge."
        echo "{\"continue\": false, \"stopReason\": \"$MSG\"}"
        exit 0
    fi
fi

exit 0
```

**`.claude/verify-docs.sh`** — Bloqueia merge/PR sem atualização de documentação quando há mudanças em `src/`:

```bash
#!/bin/bash
COMMAND=$(jq -r '.tool_input.command' 2>/dev/null)

if echo "$COMMAND" | grep -qE "git merge|git push.*main|git push.*develop|gh pr create"; then
    CURRENT_BRANCH=$(git branch --show-current)
    if [ "$CURRENT_BRANCH" != "main" ]; then
        BASE_COMMIT=$(git merge-base main HEAD 2>/dev/null)
        MODIFIED_FILES=$(git diff --name-only "$BASE_COMMIT"...HEAD 2>/dev/null)
        LOCAL_MODIFIED=$(git status --porcelain | awk '{print $2}')
        ALL_FILES=$(echo -e "${MODIFIED_FILES}\n${LOCAL_MODIFIED}" | sort -u)

        HAS_CODE_CHANGES=false
        HAS_DOCS_CHANGES=false
        echo "$ALL_FILES" | grep -qE "^src/" && HAS_CODE_CHANGES=true
        echo "$ALL_FILES" | grep -qE "^docs/|^\.claude/memory/|\.md$" && HAS_DOCS_CHANGES=true

        if [ "$HAS_CODE_CHANGES" = true ] && [ "$HAS_DOCS_CHANGES" = false ]; then
            MSG="⚠️ [BLOQUEIO DE DOCUMENTAÇÃO] Alterações em src/ detectadas sem atualização de docs/. Atualize a documentação antes do merge."
            echo "{\"continue\": false, \"stopReason\": \"$MSG\"}"
            exit 0
        fi
    fi
fi

exit 0
```

---

### 6.2 Blueprint 2: Instruções Paritárias do Repositório (`CLAUDE.md` / `GEMINI.md`)

> ⚠️ **Paridade Conceitual, Não Literal**: Os arquivos `CLAUDE.md` e `GEMINI.md` compartilham as **mesmas regras arquiteturais** (DDD, Vertical Slice, Graphify, idioma, Alembic) mas **não são textualmente idênticos**. O `CLAUDE.md` é escrito em inglês e focado em código e extensibilidade local (skills, agents, hooks). O `GEMINI.md` é escrito em pt-BR e focado em workflows, MCPs, memória e ADRs. A paridade está nas regras de comportamento, não no texto verbatim.

#### Conteúdo Mínimo Obrigatório em Ambos

Os seguintes blocos temáticos **devem estar presentes** nos dois arquivos, adaptados ao idioma e formato de cada CLI:

| Bloco | CLAUDE.md | GEMINI.md |
| :--- | :--- | :--- |
| Arquitetura (DDD + Vertical Slice) | ✅ (inglês) | ✅ (pt-BR) |
| Política de idioma pt-BR/EN-US | ✅ | ✅ |
| Regras de Banco / Alembic | ✅ | ✅ |
| Diretriz Graphify Before Grep/Glob | ✅ | ✅ |
| Comandos de desenvolvimento (`make *`) | ✅ | ✅ |
| Skills e Agentes locais | ✅ (`.claude/`) | ✅ (`.agents/`) |
| Memória e KIs | Referência ao `.claude/memory/` | Referência ao `.gemini/memory/` |
| Conventional Commits | ✅ | ✅ (tabela completa) |
| ADRs obrigatórios | Referência | ✅ (explicitado como mandatório) |

#### Template Mínimo de `CLAUDE.md`

```markdown
# CLAUDE.md

## Commands Reference
- **Load Env**: `source scripts/load-env.sh`
- **Setup Hooks**: `make setup-gemini-hook`
- **Dev (Docker)**: `make dev`
- **Run Local**: `make run`
- **Format**: `make format` | **Lint**: `make lint`
- **Tests**: `make test` | **Coverage**: `make test-cov`
- **Migration**: `make migration msg="your message"` | **Apply**: `make migrate`
- **Memory Sync**: `make pull-memory` / `make push-memory`
- **AI Sandbox**: `make jail-openclaude` / `make jail-gemini`

## Architecture: DDD & Vertical Slice
Each domain lives in `src/app/{module}/` with:
- `models.py` — SQLAlchemy 2.0 entities (Mapped style)
- `schemas.py` — Pydantic v2 DTOs
- `repository.py` — ABC interface + SQLAlchemy impl
- `service.py` — Pure domain business logic
- `use_cases.py` — Orchestration layer, **exclusive owner of commit()**
- `router.py` — FastAPI routes, parsing, DI only

## Language Policy
- **Documentation** (`docs/`): Português BR (pt-BR)
- **Code & Commits**: English (EN-US), Conventional Commits format

## Database & Migrations (Alembic)
- No wildcard imports in `alembic/env.py`
- All models must be imported in `src/app/models_registry.py`
- DDL must be defensive: always check `has_table`/`has_column` before changes

## graphify (Knowledge Graph — Mandatory)
- **MANDATORY**: Run `graphify query "<question>"` BEFORE any `Grep` or `Glob`
- After code changes: `graphify update .` (automated via PostToolUse hook)
- After `.graphifyignore` changes: `graphify extract . --force --code-only`

## Claude Code Extensibility (Skills & Agents)
- `.claude/skills/create-migration/` — Defensive Alembic migrations
- `.claude/skills/gen-route-test/` — FastAPI route test generation
- `.claude/agents/migration-verifier.md` — DDL audit subagent
- `.claude/agents/knowledge-graph-curator.md` — Graph curation subagent
```

#### Template Mínimo de `GEMINI.md`

```markdown
# GEMINI.md — Diretrizes do Projeto

## 1. Stack Técnica
- **Linguagem**: Python 3.12+ / **Gerenciador**: `uv`
- **Framework**: FastAPI / **ORM**: SQLAlchemy 2.0 Async + aiomysql
- **Migrações**: Alembic / **Infra**: Docker & Docker Compose

## 2. Arquitetura (DDD + Vertical Slice)
Cada módulo em `src/app/{modulo}/` contém:
- `models.py`, `schemas.py`, `repository.py`, `service.py`, `use_cases.py`, `router.py`

## 3. Workflows de Desenvolvimento
- Local: `make run` | Docker: `make dev` | Testes: `make test`
- Migração: `make migration msg="mensagem"` | Aplicar: `make migrate`
- Carregar env: `source scripts/load-env.sh`
- Memória: `make pull-memory` / `make push-memory`

## 4. Skills e Regras do Agente
- Skills em `.agents/skills/` e `.gemini/skills/`
- SEMPRE consultar KIs antes de iniciar qualquer tarefa
- Memórias salvas em `.gemini/memory/` (NUNCA no diretório global)

## 5. Controle de Versão (Git)
- Commits: Inglês (EN-US), padrão Conventional Commits obrigatório
- PROIBIDO: mensagens genéricas como "fix: ajustes" ou "chore: wip"

## 6. Documentação
- Toda documentação em pt-BR
- ADRs em `docs/adrs/` — LEITURA OBRIGATÓRIA antes de qualquer alteração arquitetural
- Specs: `docs/ai/specs/` | Plans: `docs/ai/plans/` | Reports: `docs/reports/`

## graphify
- **MANDATORY**: `graphify query "<pergunta>"` ANTES de qualquer Grep/Glob/search_file_content
- Subagentes despachados DEVEM incluir a diretiva de usar graphify
```

---

### 6.2.1 Blueprint Gemini `settings.json` (`.gemini/settings.json`)

O Gemini CLI utiliza seu próprio arquivo de configuração com nomenclatura diferente dos hooks Claude (`BeforeTool`/`AfterTool` em vez de `PreToolUse`/`PostToolUse`) e inclui a configuração dos **servidores MCP**:

```json
{
  "general": {
    "enableNotifications": true,
    "plan": {
      "directory": "docs/ai/plan/*"
    }
  },
  "experimental": {
    "worktrees": true,
    "modelSteering": true,
    "contextManagement": true,
    "generalistProfile": true,
    "autoMemory": true
  },
  "mcpServers": {
    "sequential_thinking": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"]
    },
    "StitchMCP": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://stitch.googleapis.com/mcp", "--header", "X-Goog-Api-Key: ${STITCH_API_KEY}"],
      "env": {}
    },
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN}"
      }
    }
  },
  "hooks": {
    "BeforeTool": [
      {
        "matcher": "read_file|list_directory|search_file_content|grep_search|run_shell_command",
        "hooks": [
          {
            "type": "command",
            "command": "/Users/<SEU_USER>/.local/bin/graphify hook-guard gemini"
          }
        ]
      }
    ],
    "AfterTool": [
      {
        "matcher": "write_file|edit_file",
        "hooks": [
          {
            "type": "command",
            "command": "(jq -r \".tool_response.filePath // .tool_input.file_path\" | grep -E \"\\.(py|md)$\" && /Users/<SEU_USER>/.local/bin/graphify update .) || true",
            "statusMessage": "Atualizando grafo de conhecimento com Graphify..."
          }
        ]
      }
    ]
  }
}
```

> ⚠️ **Diferença de nomenclatura**: Gemini usa `BeforeTool`/`AfterTool`; Claude usa `PreToolUse`/`PostToolUse`. Os servidores MCP listados requerem as variáveis de ambiente correspondentes carregadas via `source scripts/load-env.sh`.

---

### 6.3 Blueprint 3: Prompt do Subagente de Auditoria DDL (`.claude/agents/migration-verifier.md`)

Este arquivo define o subagente isolado especializado em verificar a segurança de arquivos de migração gerados pelo Alembic antes do merge.

```markdown
---
name: migration-verifier
description: Subagente especializado para auditoria defensiva de migrações DDL Alembic com contexto zerado
tools: Read, Grep, Glob, Bash
---

Você é um subagente especializado em auditoria de banco de dados e migrações Alembic. Sua missão única é validar se os arquivos de migração em `alembic/versions/` cumprem com a política de DDL defensiva e não representam riscos para o banco em produção.

### 🚨 Regras Mandatórias de Validação DDL

1. **Idempotência e Verificações Defensivas**:
   - Para toda criação de tabela (`op.create_table`), deve haver verificação via `inspector.has_table()`.
   - Para toda adição de coluna (`op.add_column`), deve haver verificação via `inspector.has_column()`.
   - Para toda remoção ou alteração, deve-se validar o estado prévio da tabela/coluna.

2. **Prevenção de Locks e Downtime**:
   - Operações `NOT NULL` em colunas existentes devem incluir valor `server_default` temporário para evitar travamento da tabela em produção.
   - Proibido executar `op.drop_table` sem fallback de confirmação e backup prévio.

3. **Inspecção de Código**:
   - Utilize a inspeção via `sa.inspect(op.get_bind())` no corpo da migração.

### 📝 Instruções de Execução
1. Analise o arquivo de migração mais recente criado em `alembic/versions/`.
2. Verifique se as funções `upgrade()` e `downgrade()` estão devidamente implementadas e simétricas.
3. Garanta que a migração foi importada em `src/app/models_registry.py`.

### 📤 Formato de Retorno
Emita um relatório conciso em **pt-BR** informando:
- **Status**: [APROVADO / REJEITADO]
- **Pontos de Atenção**: Lista de riscos ou trechos não defensivos encontrados.
- **Ação Recomendada**: Correções específicas a aplicar na migração.
```

---

### 6.4 Blueprint 4: Fixtures de Testes em Memória (`tests/conftest.py`)

Fixture para isolamento de testes de rotas FastAPI com SQLite assíncrono em memória. O arquivo real do projeto serve como referência canônica.

> ⚠️ **Detalhes Críticos de Implementação**:
> - O módulo de injeção de dependência é `src.core.deps` (não `src.core.dependencies`)
> - O import de `src.app.models_registry` é **obrigatório** — sem ele o SQLAlchemy não mapeia os modelos e o `create_all` não cria as tabelas
> - O engine usa scope `session` (não `function`) para performance — o schema é recriado por teste, não o engine
> - As variáveis de ambiente devem ser setadas antes dos imports da aplicação

```python
import os

# Configurar ambiente de teste ANTES de importar a aplicação
os.environ["ENV"] = "test"
os.environ["ONESIGNAL_APP_ID"] = ""
os.environ["ONESIGNAL_API_KEY"] = ""

import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from src.core.database import Base
from src.core.deps import get_uow  # ATENÇÃO: 'deps', não 'dependencies'
from src.core.unit_of_work import UnitOfWorkImpl
import src.app.models_registry  # noqa: F401 — OBRIGATÓRIO: força o carregamento dos mappers SQLAlchemy

# SQLite assíncrono em memória para isolamento total
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
def test_engine():
    """Engine compartilhado entre todos os testes da sessão (performance)."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    yield engine
    engine.sync_engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def init_db(test_engine):
    """Cria e destrói o schema completo por teste (isolamento de estado)."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine, init_db) -> AsyncSession:
    """Sessão assíncrona limpa por teste."""
    async_session = async_sessionmaker(
        test_engine, expire_on_commit=False, class_=AsyncSession
    )
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def uow(db_session: AsyncSession):
    """Unit of Work usando a sessão de teste em memória."""
    unit_of_work = UnitOfWorkImpl(session_factory=lambda: db_session)
    yield unit_of_work


@pytest_asyncio.fixture(scope="function")
async def client(uow):
    """Cliente HTTP com override de get_uow e cleanup obrigatório via try/finally."""
    from httpx import AsyncClient, ASGITransport
    from src.main import app

    app.dependency_overrides[get_uow] = lambda: uow
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()  # Limpeza obrigatória entre testes
```

---

### 6.5 Blueprint 5: Git Pre-Commit Hook e Scripts de Sincronização de Memória

> 💡 **Nota de Referência**: Para o guia completo de gestão de variáveis de ambiente, segredos e deployment de produção, consulte o [Guia DevOps de Variáveis de Produção](docs/reports/2026-07-14-guia-devops-variaveis-producao.md).

O hook real instalado via `make setup-gemini-hook` em `.git/hooks/pre-commit` é deliberadamente simples — delega toda a lógica de sincronização para os scripts especializados:

```bash
#!/bin/bash
# Sync OpenClaude memory before commit
./.claude/sync-claude-memory.sh pull
```

A sincronização real é feita pelos dois scripts abaixo, que usam `rsync` para mover memórias entre o repositório local e os diretórios globais dos assistentes.

#### `.gemini/sync-memory.sh` — Sincronização da Memória do Gemini CLI

```bash
#!/bin/bash

PROJECT_ROOT=$(git rev-parse --show-toplevel)
PROJECT_BASENAME=$(basename "$PROJECT_ROOT")

# O Gemini armazena memória em ~/.gemini/tmp/<nome-do-projeto>/memory/
CONFIG_HOME="$HOME/.gemini"
GLOBAL_MEM_PATH="$CONFIG_HOME/tmp/$PROJECT_BASENAME/memory/"
LOCAL_MEM_PATH="$PROJECT_ROOT/.gemini/memory/"

if [ "$1" == "pull" ]; then
  echo "Pulling memory from system Gemini to local..."
  mkdir -p "$LOCAL_MEM_PATH"
  if [ -d "$GLOBAL_MEM_PATH" ]; then
    rsync -av --include="*/" --include="*.md" --exclude="*" "$GLOBAL_MEM_PATH" "$LOCAL_MEM_PATH"
    git add "$LOCAL_MEM_PATH"  # Auto-staging para o commit
    echo "Memory pulled successfully."
  else
    echo "Error: Run 'make push-memory' first to initialize."; exit 1
  fi
elif [ "$1" == "push" ]; then
  echo "Pushing memory from local to system Gemini..."
  mkdir -p "$GLOBAL_MEM_PATH"
  rsync -av --include="*/" --include="*.md" --exclude="*" "$LOCAL_MEM_PATH" "$GLOBAL_MEM_PATH"
  echo "Memory pushed successfully."
else
  echo "Usage: ./.gemini/sync-memory.sh [pull|push]"
  exit 1
fi
```

#### `.claude/sync-claude-memory.sh` — Sincronização da Memória do OpenClaude

```bash
#!/bin/bash

PROJECT_ROOT=$(git rev-parse --show-toplevel)
# OpenClaude sanitiza o path: substitui caracteres especiais por hífen
SANITIZED_PATH=$(echo "$PROJECT_ROOT" | sed 's/[^a-zA-Z0-9]/-/g')

# Resolve diretório home do OpenClaude (~/.openclaude com fallback para ~/.claude)
CONFIG_HOME="$HOME/.openclaude"
if [ ! -d "$CONFIG_HOME" ] && [ -d "$HOME/.claude" ]; then
  CONFIG_HOME="$HOME/.claude"
fi

GLOBAL_MEM_PATH="$CONFIG_HOME/projects/$SANITIZED_PATH/memory/"
LOCAL_MEM_PATH="$PROJECT_ROOT/.claude/memory/"

if [ "$1" == "pull" ]; then
  echo "Pulling memory from global OpenClaude to local..."
  mkdir -p "$LOCAL_MEM_PATH"
  rsync -av --delete --include="*/" --include="*.md" --exclude="*" "$GLOBAL_MEM_PATH" "$LOCAL_MEM_PATH"
  git add "$LOCAL_MEM_PATH"  # Auto-staging para o commit
  echo "Memory pulled successfully."
elif [ "$1" == "push" ]; then
  echo "Pushing memory from local to global OpenClaude..."
  mkdir -p "$GLOBAL_MEM_PATH"
  rsync -av --delete --include="*/" --include="*.md" --exclude="*" "$LOCAL_MEM_PATH" "$GLOBAL_MEM_PATH"
  echo "Memory pushed successfully."
else
  echo "Usage: ./.claude/sync-claude-memory.sh [pull|push]"
  exit 1
fi
```

> 💡 **Fluxo completo**: `git commit` → hook `.git/hooks/pre-commit` → `.claude/sync-claude-memory.sh pull` → rsync da memória global para local → `git add .claude/memory/` → commit com código + memórias sincronizadas.

---

### 6.6 Blueprint 6: Sandbox e Filtros (`.ai-jail` e `.graphifyignore`)

> 💡 **Nota de Referência**: Para a especificação completa da sandbox de segurança, limites de acesso a arquivos e permissões do agente, consulte o [Guia de AI Jail e Sandbox Setup](docs/guides/guia-ai-jail-sandbox.md).

Configuração pronta dos arquivos de restrição de sandbox e exclusão de indexação do grafo de conhecimento.

#### 1. `.ai-jail` (Isolamento de Diretórios Sensíveis)

O `.ai-jail` usa formato **TOML** (não INI) e define quais diretórios o agente pode ler/escrever (`rw_maps`) e quais são somente leitura (`ro_maps`):

```toml
# ai-jail sandbox configuration
# https://github.com/akitaonrails/ai-jail
# Regenerar com: ai-jail --clean --init

command = ["openclaude"]
rw_maps = [
    "~/.openclaude",
    "~/.gemini",
    "~/.claude",
    "~/.cache",
    "~/.local",
]
ro_maps = ["~/.gitconfig"]
```

> 💡 O `command` define qual CLI é isolado. Para usar Gemini, substitua por `["gemini"]`. Instalar via `make jail-setup` e rodar via `make jail-openclaude` ou `make jail-gemini`.

#### 2. `.graphifyignore` (Exclusão de Indexação do Graphify)

```gitignore
# Logs de Chat, Planos Voláteis e Metadados de IA / Agentes
docs/ai/chats/
docs/ai/plans/
.agents/
.claude/
.gemini/
.openclaude/
.superpowers/

# Ambientes Virtuais e Dependências
.venv/
venv/
node_modules/

# Artefatos de Build, Caches e Bytecode
__pycache__/
*.pyc
.pytest_cache/
.ruff_cache/
dist/
build/
*.egg-info/
graphify-out/cache/
**/__init__.py

# Relatórios de Cobertura de Testes
.coverage
coverage/
htmlcov/

# Controle de Versão e Worktrees
.git/
.worktrees/
```

> ⚠️ **Diferença crítica do blueprint anterior**: Os diretórios `.agents/`, `.claude/`, `.gemini/`, `.openclaude/` e `.superpowers/` devem ser explicitamente ignorados para que o grafo indexe apenas código de produção. O arquivo usa sintaxe `gitignore`, não INI.

---

## 🛠️ 7. Playbook do Desenvolvedor, Matriz de Maturidade e Checklist

Esta seção consolida o guia prático operacional para novos desenvolvedores e agentes de IA, apresentando o playbook de extensibilidade, a matriz de maturidade em 3 níveis e a checklist de auditoria para certificação de Harness Nível 3.

---

### 7.1 Playbook Operacional para Desenvolvedores e Agentes

#### 1. Como Criar e Estruturar Novas Skills (`.claude/`, `.gemini/`, `.agents/`)

As skills estendem o comportamento do agente com automações locais. Para criar uma nova skill no repositório:

1. **Localização**: Defina o escopo da skill e crie o diretório correspondente contendo o arquivo `SKILL.md`:
   - Específica para Claude: `.claude/skills/<nome-da-skill>/`
   - Específica para Gemini: `.gemini/skills/<nome-da-skill>/`
   - Compartilhada (Rules/Genéricas): `.agents/skills/<nome-da-skill>/`
2. **Estrutura Obrigatória do Cabeçalho YAML (Frontmatter)**:
   - `name`: Identificador único da skill.
   - `description`: Descrição clara do propósito da skill e quando ela deve ser invocada.
3. **Template Padrão de `SKILL.md`**:

````markdown
---
name: minha-skill
description: Descricao clara da finalidade e gatilhos para invocacao desta skill
---

# Titulo da Skill

## Contexto e Objetivo
Descricao detalhada do objetivo operacional.

## Passos de Execucao
1. Passo 1 de execucao.
2. Passo 2 de execucao.

## Exemplo de Comando ou Output Esperado
```bash
# Exemplo operacional
```
````

4. **Boas Práticas de Implementação**:
   - Mantenha o escopo focado em uma única responsabilidade.
   - Evite premissas implícitas; especifique caminhos de arquivo absolutos ou baseados no diretório raiz do projeto.
   - Teste a invocação da skill usando `/nome-da-skill` na conversa com o agente.

#### 2. Como Atualizar e Consultar Memórias Locais e de Equipe

A memória persistente previne regressões e garante a continuidade do conhecimento.

- **Memórias Privadas (`private`)**:

  - Armazenadas em `.openclaude/projects/.../memory/` ou `.gemini/memory/local/`.
  - Usadas para preferências de ambiente local, atalhos de ferramentas e configurações pessoais.
  - Não devem ser commitadas no Git.
- **Memórias de Equipe (`team`)**:

  - Armazenadas em `.gemini/memory/team/` ou `.openclaude/.../memory/team/`.
  - Usadas para regras de banco de dados, convenções de rotas FastAPI, incidentes superados e decisões de arquitetura (ADRs).
  - Devem conter o cabeçalho YAML com `type: team`, `name` e `description`.
  - **Consulta**: O agente lê automaticamente os arquivos `MEMORY.md` e o conteúdo das memórias de equipe na inicialização.
  - **Atualização**: Para registrar um novo aprendizado, crie ou edite um arquivo `.md` na pasta de memórias do time. O Git Pre-Commit Hook fará o auto-staging transparente no próximo commit (`make setup-gemini-hook`).

#### 3. Como Gerenciar Hooks e Interagir com o Harness

- **Visualização de Hooks Ativos**: Verifique o arquivo `.claude/settings.json` para inspecionar os hooks registrados para `PreToolUse` e `PostToolUse`.
- **Inativação Temporária / Bypassing**: Caso precise realizar um commit de emergência sem disparar a suíte completa de hooks, utilize a flag `--no-verify`:
  ```bash
  git commit -m "fix: emergency patch" --no-verify
  ```

- **Interação Fluida**: Lembre-se que o agente executa `make format && make lint` automaticamente a cada edição de código Python. Não solicite formatadores manualmente, pois o Harness faz isso de forma zero-turn.

#### 4. Identificação e Gestão de Sessões (`/color` e `/rename`) (MANDATÓRIO)

- **Objetivo**: Evitar desorientação e perda de contexto ao operar múltiplas janelas, terminais ou sessões concorrentes de desenvolvimento.
- **Diretiva Obrigatória**: No início de cada nova sessão ou ao alternar o foco temático de desenvolvimento (ex: de refatoração para debugging, ou entre módulos distintos), execute compulsoriamente:
  1. `/color <cor>`: Atribui uma identidade visual única à sessão no terminal.
  2. `/rename <título-curto-do-tópico>`: Renomeia a aba/sessão com a descrição precisa da tarefa em andamento.
- **Benefício Operacional**: Garante rápida alternância de contexto no terminal e integridade de rastreamento entre sessões de longa duração.


---

### 7.2 Matriz de Maturidade do Harness

A matriz a seguir define os 3 Níveis de Maturidade do Harness para cada um dos 7 pilares de engenharia, servindo como modelo de diagnóstico e evolução para o repositório.

| Pilar do Harness                         | Nível 1: Incipiente                                                                      | Nível 2: Intermediário                                                                  | Nível 3: Maduro / Robusto (Target)                                                                                                                       |
| :--------------------------------------- | :---------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1. Instruções e Convenções** | Ausente ou prompt informal ad-hoc. Sem arquivo de instrução centralizado.               | Arquivo `CLAUDE.md` básico sem especificações lógicas de DDD ou política de idioma. | `CLAUDE.md` e `GEMINI.md` paritários, com DDD Vertical Slice, políticas rígidas pt-BR/EN-US e standards de infraestrutura.                         |
| **2. Formatação Zero-Turn**      | Manual. Erros de linter exigem múltiplos turnos de correção pelo agente.               | Scripts manuais de `make format` executados periodicamente pelo desenvolvedor.           | Interceptação determinística via Hooks JSON `PreToolUse`/`PostToolUse` rodando `Ruff` silenciosamente a cada edição.                            |
| **3. Navegação com Graphify**    | Varreduras puras via `Grep`/`Glob` consumindo dezenas de milhares de tokens por busca. | `Graphify` instalado, porém utilizado apenas manualmente a pedido do usuário.         | Diretriz mandatória "Graphify Before Grep/Glob" com hook-guard educativo e injeção compulsória em subagentes.                                         |
| **4. Skills Encadeadas**           | Sem skills configuradas ou usando apenas comandos isolados de CLI.                        | Skills de domínio isoladas sem integração metodológica com o ciclo de vida.           | Encadeamento orquestrado: Superpowers (`/brainstorming`, `/writing-plans`) + Matt Pocock (`/grill-me`) + Skills de Domínio (`/create-migration`). |
| **5. Subagentes de Verificação** | Auditorias e revisões executadas dentro do mesmo chat, poluindo o contexto.              | Subagentes criados pontualmente sem padronização de prompts ou isolamento.              | Subagentes especializados (ex: `migration-verifier`) com contexto zerado e saída sintética padronizada.                                                |
| **6. Memória & Auto-Staging**     | Sem persistência de conhecimento. Reaprendizado constante a cada nova sessão.           | Memórias registradas em arquivos locais sem auto-staging no controle de versão.         | Arquitetura de memória dupla (Privada/Equipe) com auto-staging automático via Git Pre-Commit Hooks (`make setup-gemini-hook`).                        |
| **7. Testes em Memória**          | Testes acoplados a banco de dados físico de dev ou sem suíte de testes automáticos.    | Testes usando SQLite local em arquivo sem isolamento total de fixtures async.             | Fixtures em `conftest.py` usando SQLite `sqlite+aiosqlite:///:memory:`, FastAPI `dependency_overrides` e cleanup em `finally`.                     |

---

### 7.3 Checklist de Auditoria do Harness para Novos Projetos

Utilize esta checklist para auditar e certificar se um repositório ou novo projeto atingiu o Nível 3 de Maturidade do Harness antes de iniciar o desenvolvimento autônomo.

#### 📋 1. Instruções e Convenções Paritárias (Pilar 1)

- [ ] Arquivo `CLAUDE.md` presente na raiz do repositório.
- [ ] Arquivo `GEMINI.md` presente na raiz com conteúdo conceitualmente paritário ao `CLAUDE.md`.
- [ ] Especificação explícita da arquitetura (DDD e Vertical Slice) nos arquivos de instrução.
- [ ] Política de idiomas definida: documentação em **pt-BR**, código e commits em **EN-US** (Conventional Commits).

#### 📋 2. Formatação e Linting Zero-Turn (Pilar 2)

- [ ] Arquivo `.claude/settings.json` configurado com hooks `PreToolUse` e `PostToolUse`.
- [ ] Hook de interceptação de arquivos `.py` executando `make format && make lint` (`Ruff`) silenciosamente.
- [ ] Linter configurado e validado sem ruídos no terminal.

#### 📋 3. Navegação Estruturada por Grafo (Pilar 3)

- [ ] Ferramenta `graphify` instalada e funcional na máquina de desenvolvimento.
- [ ] Grafo inicial gerado em `graphify-out/graph.json`.
- [ ] Arquivo `.graphifyignore` configurado omitindo diretórios temporários, testes e relatórios.
- [ ] Hook `PostToolUse` configurado para executar `graphify update . &` em background após edições.
- [ ] Diretriz "Graphify Before Grep/Glob" presente nas instruções e pronta para ser injetada em subagentes.

#### 📋 4. Taxonomia e Encadeamento de Skills (Pilar 4)

- [ ] Skills do Framework Superpowers (`superpowers:*`) disponíveis no ambiente.
- [ ] Skill `/grill-me` (Matt Pocock / Agentic Engineering) disponível para sabatina de especificações.
- [ ] Skills de domínio criadas e versionadas em `.claude/skills/` (`create-migration`, `gen-route-test`, etc.).
- [ ] Fluxo de transição entre `/brainstorming` -> `/grill-me` -> `/writing-plans` testado e validado.

#### 📋 5. Subagentes de Verificação Isolados (Pilar 5)

- [ ] Diretório `.claude/agents/` criado e versionado.
- [ ] Subagente `migration-verifier.md` configurado com regras de DDL defensivas (`has_table`, `has_column`).
- [ ] Prompts dos subagentes configurados com contexto zerado e saída sintética de aprovação/rejeição.

#### 📋 6. Memória Persistente e Git Hooks (Pilar 6)

- [ ] Estrutura de memória de equipe inicializada em `.gemini/memory/team/`.
- [ ] Script de Git Pre-Commit Hook configurado em `.git/hooks/pre-commit` (instalável via `make setup-gemini-hook`).
- [ ] Auto-staging de memórias ativado e validado ao executar um commit no repositório.

#### 📋 7. Infraestrutura de Testes em Memória (Pilar 7)

- [ ] Arquivo `tests/conftest.py` configurado com SQLite assíncrono em memória (`sqlite+aiosqlite:///:memory:`).
- [ ] Fixture `client` utilizando `app.dependency_overrides[get_uow]` para isolamento total das rotas FastAPI.
- [ ] Bloco `try ... finally` garantindo `app.dependency_overrides.clear()` ao término de cada teste.
- [ ] Comando `make test` ou `pytest` executando a suíte de testes com sucesso e tempo total inferior a 5 segundos.

