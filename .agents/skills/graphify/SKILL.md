---
name: graphify
description: Executa a extração, consulta determinística ou atualização do Knowledge Graph do projeto UrgenSight
---

# Skill: graphify

Esta skill permite inspecionar, consultar ou regenerar o Knowledge Graph estrutural do repositório (`graphify-out/`).

## Comandos Principais
- **Consulta contextual**: `graphify query "<dúvida ou conceito>"`
- **Rastreamento de dependências entre nós**: `graphify path "<EntidadeA>" "<EntidadeB>"`
- **Explicação de componente/módulo**: `graphify explain "<arquivo_ou_funcao>"`
- **Atualização incremental**: `graphify update .` (ou `make graphify`)

## Diretriz de Uso Obrigatório
Sempre consulte o grafo antes de realizar buscas textuais brutas (`grep`/`find`/`Grep`/`Glob`) em explorações arquiteturais.
