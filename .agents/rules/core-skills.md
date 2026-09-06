# Regras Compartilhadas entre Agentes (Claude Code & Gemini CLI)

1. **Prioridade de Automação**: Sempre invoque `make test`, `make lint` e `make format` antes de concluir qualquer tarefa de código.
2. **Padrão de Commits**: Mensagens de commit devem seguir rigorosamente o padrão **Conventional Commits em português (PT-BR)** (ex: `feat(api): adicionar endpoint de predicao`, `fix(treino): corrigir calculo de f1`, `docs(ai): atualizar especificacao`).
3. **Graph First**: Consulte os grafos em `graphify-out/` para entender símbolos e dependências antes de editar arquivos complexos.
4. **Isolamento de Testes**: Não dependa de serviços externos ou GPU em testes unitários.
5. **Governança de Artefatos**: Salve especificações, planos e relatórios exclusivamente em `docs/ai/`.
