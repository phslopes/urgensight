# Regras Compartilhadas entre Agentes (Claude Code & Gemini CLI)

1. **Prioridade de Automação**: Sempre invoque `make test`, `make lint` e `make format` antes de concluir qualquer tarefa de código.
2. **Graph First**: Consulte os grafos em `graphify-out/` para entender símbolos e dependências antes de editar arquivos complexos.
3. **Isolamento de Testes**: Não dependa de serviços externos ou GPU em testes unitários.
4. **Governança de Artefatos**: Salve especificações, planos e relatórios exclusivamente em `docs/ai/`.
