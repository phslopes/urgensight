---
name: ai-artifacts-directory-convention
description: Todos os artefatos de IA (specs, plans, reports) devem ser salvos exclusivamente em docs/ai/
type: feedback
---

Todos os artefatos gerados por agentes de IA (especificações de design, planos de implementação, relatórios e guias) devem ser salvos estritamente dentro da pasta `docs/ai/` (subpastas: `docs/ai/specs/`, `docs/ai/plans/`, `docs/ai/reports/`, `docs/ai/guides/`). É expressamente proibido salvar artefatos na pasta `docs/superpowers/`.

**Why:** Centralizar e padronizar toda a documentação, governança e artefatos de agentes de IA na estrutura unificada `docs/ai/` do projeto UrgenSight.
**How to apply:** Ao usar skills como `brainstorming`, `writing-plans` ou ao gerar relatórios/especificações técnicas, sempre salvar os arquivos resultantes nos subdiretórios apropriados dentro de `docs/ai/`.
