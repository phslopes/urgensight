
# Guia de Graph Engineering para Agentes de IA: Navegação por Knowledge Graphs no Claude Code e Gemini CLI

> **Objetivo:** Este guia fornece um passo a passo completo e agnóstico de linguagem ou framework para transformar qualquer repositório de código em um **Knowledge Graph (Grafo de Conhecimento)** operacional. Ele instrui assistentes agênticos (Claude Code, Gemini CLI e OpenClaude) a navegar por relacionamentos e contextos de código com precisão determinística, reduzindo o consumo de tokens em até 70% e eliminando alucinações durante explorações.

---

## 1. O Problema: "Full Codebase Scanning" vs. Navegação por Grafo

Quando um agente de IA recebe uma tarefa em um repositório médio ou grande, o comportamento padrão costuma ser ineficiente:

* Executar múltiplos `grep`, `find` ou `cat` sucessivos.
* Ler arquivos inteiros apenas para entender dependências ou chamadas de métodos.
* Poluir a janela de contexto da LLM com código irrelevante, aumentando custos e reduzindo a precisão do raciocínio.

### A Solução: Graph Engineering (Knowledge Graphs)

Em vez de forçar a LLM a ler o código-fonte como texto plano, o **Graph Engineering** constrói um grafo estruturado local (via parsing de AST) que mapeia entidades (classes, funções, módulos, rotas, tipos) e seus relacionamentos (importa, chama, herda, implementa).

O agente consulta primeiro o grafo (`graphify query`, `graphify path`, `graphify explain`) para obter um subgrafo enxuto e orientado antes de tocar em qualquer arquivo individual.

---

## 2. Tabela Comparativa de Ferramentas de Graph Engineering

| Ferramenta                                 | Tipo de Integração                                   | Principais Recursos                                                                                                           | Casos de Uso Ideais                                                                                               |
| :----------------------------------------- | :----------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------- |
| **Graphify** (`graphifyy` no PyPI) | Skill nativa CLI (`/graphify`) e MCP Server opcional | Extração via AST sem custo de LLM, gera`graph.json`, `graph.html` e `GRAPH_REPORT.md`, com suporte a 20+ assistentes. | **Padrão Geral do Mercado:** Ideal para navegação autônoma, mapeamento de código e economia de tokens. |
| **code-review-graph** (CRG)          | MCP Server + CLI                                       | Mapeamento baseado em SQLite/AST com suporte a análise de raio de impacto (*blast radius*).                                | Foco em Code Review rigoroso e análise de impacto de mudanças.                                                  |
| **Understand Anything**              | Plugin / Marketplace                                   | Dashboard visual interativo e tours guiados pela arquitetura.                                                                 | Onboarding de novos desenvolvedores e documentação visual.                                                      |

---

## 3. Implementação Prática — Claude Code (`.claude/`)

### Passo 1: Instalação da CLI e Skill

No terminal, instale o pacote CLI e registre a skill no escopo do seu projeto:

```bash
# Instala a CLI do Graphify (PyPI: graphifyy)
uv tool install graphifyy  # ou: pip install graphifyy

# Registra a skill localmente no projeto (.claude/skills/graphify/)
graphify install --project --platform claude
```

### Passo 2: Geração Inicial do Grafo

Abra sua sessão do Claude Code e execute o comando inicial de indexação:

```bash
/graphify .
```

Isso criará a pasta `graphify-out/` contendo:

* `graph.json`: O grafo de conhecimento em formato estruturado.
* `graph.html`: Visualizador interativo em navegação visual.
* `GRAPH_REPORT.md`: Relatório textual com nós centrais, comunidades e pontos de acoplamento.

### Passo 3: Configuração das Diretrizes de Autonomia (`CLAUDE.md`)

Adicione ou atualize a seção `## graphify` no seu arquivo `CLAUDE.md` (ou `.claude/CLAUDE.md`) para forçar o agente a usar o grafo autonomamente:

```markdown
## graphify (Uso Autônomo)

Este repositório possui um Grafo de Conhecimento indexado em `graphify-out/`.

Diretrizes Obrigatórias para Agentes:
- **Graphify Antes de Grep/Glob (Obrigatório)**: O agente DEVE SEMPRE executar consultas ao graphify (`graphify query "<pergunta>"`, `graphify path` ou `graphify explain`) para exploração e navegação no código ANTES de utilizar ferramentas de busca textual ou navegação manual por arquivos (`Grep`, `Glob`, `grep` ou `find`).
- **Diretiva de Despacho de Subagentes**: Ao despachar qualquer subagente para tarefas de exploração de código ou depuração, inclua OBRIGATORIAMENTE no prompt do subagente a instrução de usar o `graphify` (`graphify query`, `graphify path`, `graphify explain`) antes de qualquer busca por texto ou arquivos.
- **Uso Autônomo e Proativo**: SEMPRE use o Graphify internamente durante explorações de código, mapeamento de arquitetura, investigação de bugs ou planejamento de features. NÃO espere o usuário digitar `/graphify` ou solicitar o comando manualmente.
- **Consulta Prévia (Query First)**: Antes de ler arquivos fonte ou executar buscas genéricas (`grep`/`find`), consulte o grafo usando:
  - `graphify query "<sua dúvida/conceito>"`: Retorna um subgrafo contextualizado.
  - `graphify path "<EntidadeA>" "<EntidadeB>"`: Mapeia dependências entre dois nós.
  - `graphify explain "<arquivo_ou_funcao>"`: Explica o papel de um nó específico.
- **Atualização do Grafo**: Após editar código ou ao detectar que `graphify-out/graph.json` está desatualizado, execute `graphify update .` de forma transparente.
```

### Passo 4: Automação via Hooks (`.claude/settings.json`)

Configure hooks para garantir que o agente seja interceptado caso tente ler arquivos sem consultar o grafo e que o grafo seja atualizado a cada edição:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash|Grep",
        "hooks": [
          {
            "type": "command",
            "command": "/Users/eduardo.batista/.local/bin/graphify hook-guard search"
          }
        ]
      },
      {
        "matcher": "Read|Glob",
        "hooks": [
          {
            "type": "command",
            "command": "/Users/eduardo.batista/.local/bin/graphify hook-guard read"
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
            "command": "(jq -r '.tool_response.filePath // .tool_input.file_path' | grep -E '\\.(py|js|ts|go|rs|java|md)$' && graphify update .) || true",
            "statusMessage": "Atualizando grafo de conhecimento com Graphify..."
          }
        ]
      }
    ]
  }
}
```

### Passo 5: Agente de Curadoria (`.claude/agents/knowledge-graph-curator.md`)

Crie um subagente especializado para auditoria de arquitetura e manutenção do grafo:

```markdown
---
name: knowledge-graph-curator
description: Mantém o grafo de conhecimento do repositório (via Graphify) sincronizado após mudanças arquiteturais relevantes.
---

# Knowledge Graph Curator Agent

Você é o agente responsável por manter o grafo de conhecimento do repositório (`graphify-out/`) sincronizado e atualizado.

## Responsabilidades
1. **Atualização do Grafo**: Sempre que novos arquivos, módulos, componentes ou documentações técnicas forem criados/alterados, execute:
   ```bash
   graphify update .
```

2. **Validação**: Garanta que `graphify-out/graph.json`, `graphify-out/graph.html` e `graphify-out/GRAPH_REPORT.md` foram atualizados corretamente.

```

---

## 4. Implementação Prática — Gemini CLI / OpenClaude (`.gemini/`)

### Passo 1: Instalação da Skill para Gemini
Registre a skill no diretório local do Gemini CLI:

```bash
graphify install --project --platform gemini
```

### Passo 2: Configuração das Diretrizes no `GEMINI.md`

Adicione o mesmo bloco de instrução no seu `GEMINI.md`:

```markdown
## graphify

Rules for Autonomous Agent Exploration:
- **Graphify Before Grep/Glob**: MANDATORY: You MUST run `graphify query "<question>"` (or `graphify path` / `graphify explain`) for initial codebase exploration BEFORE executing any `Grep`, `Glob`, `grep_search`, or `search_file_content` tool calls. Only use raw search after graphify has oriented you.
- **Subagent Dispatch Directive**: When spawning or dispatching ANY subagent that involves codebase exploration, debugging, or architecture analysis, you MUST explicitly include the directive in the subagent's prompt forcing it to run `graphify` (`graphify query`, `graphify path`, or `graphify explain`) before any `Grep` or file search operations.
- **Autonomous Exploration**: ALWAYS use graphify internally during codebase explorations, architecture mapping, bug investigations, or feature planning. DO NOT wait for the user to explicitly type `/graphify` or request graphify commands manually.
- **Query First**: For any codebase or architecture question, run `graphify query "<question>"` when `graphify-out/graph.json` exists. Use `graphify path "<A>" "<B>"` for tracing relationships/dependencies and `graphify explain "<concept>"` for focused concepts.
- **Graph Updates**: After modifying code or if `graphify-out/graph.json` is missing/stale, run `graphify update .` automatically.
```

### Passo 3: Configuração de Hooks no `.gemini/settings.json`

Atualize as permissões e hooks de interceptação para o Gemini CLI:

```json
{
  "hooks": {
    "BeforeTool": [
      {
        "matcher": "read_file|list_directory|search_file_content|grep_search|run_shell_command",
        "hooks": [
          {
            "type": "command",
            "command": "/Users/eduardo.batista/.local/bin/graphify hook-guard gemini"
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
            "command": "(jq -r '.tool_response.filePath // .tool_input.file_path' | grep -E '\\.(py|js|ts|go|rs|java|md)$' && graphify update .) || true",
            "statusMessage": "Atualizando grafo de conhecimento com Graphify..."
          }
        ]
      }
    ]
  }
}
```

---

## 5. Automação no Git (Hooks Nativos)

Para que o grafo de conhecimento seja mantido atualizado no nível de controle de versão (independente do assistente de IA utilizado no momento), instale os hooks nativos do Git:

```bash
graphify hook install
```

O comando registra automaticamente em seu repositório:

1. `.git/hooks/post-commit`: Executa re-indexação incremental dos arquivos modificados a cada `git commit`.
2. `.git/hooks/post-checkout`: Re-indexa o grafo ao alternar de branch.
3. `merge driver`: Configura a resolução de conflitos para o arquivo `graphify-out/graph.json`.

---

## 6. Boas Práticas de Versionamento e Colaboração em Equipe

Para garantir que toda a equipe compartilhe o mesmo grafo sem regerações desnecessárias:

1. **Atentando-se ao `.gitignore`**:

   * **Manter no Git (comitar):**
     * `graphify-out/graph.json` (o grafo consultável)
     * `graphify-out/GRAPH_REPORT.md` (o relatório textual de arquitetura)
     * `graphify-out/graph.html` (a visualização web interativa)
   * **Ignorar no `.gitignore`:**
     * `graphify-out/cache/` ou arquivos de cache temporário.
2. **Benefício para o Time**:
   Quando um desenvolvedor baixa uma nova branch (`git pull`), o `graph.json` já estará sincronizado. Qualquer desenvolvedor ou agente de IA que iniciar uma nova sessão terá o conhecimento do repositório instantaneamente disponível sem custo de inicialização.

---

## Resumo do Fluxo de Trabalho

```
┌────────────────────────┐
│  Desenvolvedor / IA    │
│  faz uma pergunta      │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│   hook-guard do CLI    │ ── (Intercepta busca/leitura manual)
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ `graphify query <q>`   │ ── (Extrai apenas o subgrafo relevante)
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│  Agente lê 2-3 arquivos│ ── (Ação precisa e direcionada)
│  específicos do grafo  │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ Edição / Modificação   │ ── (PostToolUse hook dispara `graphify update .`)
└────────────────────────┘
```
