# ADR-0001 — Mapeamento proxy do dataset para classes de urgência

- **Status:** Aceito
- **Data:** 2026-09-01
- **Contexto da decisão:** Etapa 1 (Machine Learning) — registrado retroativamente

## Contexto

O UrgenSight precisa treinar um classificador supervisionado para as três classes
de urgência do domínio do projeto (`normal`, `atencao`, `urgente`). Isso exige um
dataset rotulado, de preferência público e verificável, para sustentar a narrativa
acadêmica do projeto.

O dataset escolhido foi o **Medical Abstracts TC Corpus**
([sebischair/Medical-Abstracts-TC-Corpus](https://github.com/sebischair/Medical-Abstracts-TC-Corpus)),
14.438 resumos de literatura médica, cada um rotulado com uma de 5 categorias
clínicas (`condition_label` de 1 a 5: Neoplasms, Digestive system diseases,
Nervous system diseases, Cardiovascular diseases, General pathological
conditions). O problema é que **o corpus não possui rótulos de urgência/triagem** —
os rótulos originais descrevem a categoria clínica do texto (que sistema do corpo é
afetado), não a gravidade ou a prioridade de atendimento do caso. Não há, no
dataset, nenhuma coluna ou anotação que corresponda diretamente a
`normal`/`atencao`/`urgente`.

## Decisão

Adotamos um **mapeamento proxy**, baseado em um critério simples de severidade
clínica típica de cada categoria original, para derivar as três classes do
projeto a partir das cinco categorias do corpus:

| Categoria original | Classe do projeto | Justificativa |
|---|---|---|
| Cardiovascular diseases (4) | **urgente** | Eventos cardiovasculares (ex.: infarto, arritmias) tipicamente exigem resposta imediata |
| Neoplasms (1) | **atencao** | Achados oncológicos requerem investigação e acompanhamento especializado, mas não são necessariamente uma emergência imediata |
| Nervous system diseases (3) | **atencao** | Condições neurológicas geralmente requerem avaliação especializada e monitoramento |
| Digestive system diseases (2) | **normal** | Predominantemente queixas/condições de rotina no corpus |
| General pathological conditions (5) | **normal** | Categoria genérica de condições de rotina |

Esse mapeamento é aplicado por `src/prepare_dataset.py`, produzindo o esquema final
`text` / `target` consumido pelo pipeline de treino.

**Limitação conhecida (preservada de `docs/dataset.md`):** este é um mapeamento
didático/proxy para fins acadêmicos, **não uma classificação clínica de triagem
real** (ex.: Manchester Protocol). Foi escolhido por produzir uma distribuição de
classes plausível (mais casos rotineiros que urgentes) e por usar um dataset
público, real e verificável — em vez de rótulos sintéticos artificiais. Qualquer
uso além do escopo acadêmico deste projeto exigiria revisão por profissionais de
saúde e um dataset com rótulos de urgência reais.

## Alternativas consideradas

**Gerar rótulos sintéticos artificiais** (ex.: sortear a classe de urgência
aleatoriamente, ou por regras de palavras-chave sobre o texto). Rejeitada: embora
permitisse controlar a distribuição de classes com precisão, produziria um
dataset sem nenhuma relação real com o conteúdo clínico do texto — o modelo
aprenderia um padrão artificial sem qualquer valor demonstrativo, e o projeto
perderia a característica de usar dados públicos e verificáveis.

**Buscar outro dataset com rótulos de urgência reais** (ex.: um dataset de triagem
hospitalar com prioridade de atendimento anotada por profissionais). Rejeitada
neste momento: datasets desse tipo, quando públicos, são raros, frequentemente
exigem credenciamento de acesso a dados de saúde (institucional ou por comitê de
ética) e não estavam disponíveis dentro do prazo e do escopo do Tech Challenge.
Permanece como direção legítima para evolução futura do projeto.

**Adotar o Protocolo de Manchester como base do mapeamento** (reclassificar as
categorias originais segundo as cores/prioridades do Manchester Triage System).
Rejeitada: o Manchester Protocol classifica com base em sinais, sintomas e
discriminadores clínicos observados no momento do atendimento, não em categoria
de doença de um resumo de literatura médica. Aplicá-lo sobre este corpus exigiria
inferir discriminadores clínicos que o texto simplesmente não contém, o que criaria
uma falsa aparência de rigor clínico sobre um mapeamento que continua sendo, na
prática, um proxy.

## Consequências

- O projeto usa um dataset público, real e citável, o que fortalece a
  reprodutibilidade e a avaliação acadêmica, mas o rótulo `target` **não deve ser
  interpretado como triagem clínica validada** em nenhum material do projeto
  (API, README, apresentação).
- A distribuição de classes resultante (mais `normal`/`atencao` que `urgente`)
  reflete a composição do corpus original, não uma epidemiologia real de urgências
  hospitalares.
- Qualquer extensão do projeto para um contexto além do acadêmico exige troca do
  dataset e do mapeamento por uma fonte com rótulos de urgência reais, validada por
  profissionais de saúde — este ADR não abre esse caminho, apenas documenta por que
  ele não foi tomado agora.
- A limitação é comunicada explicitamente em `docs/dataset.md`, para que
  avaliadores e futuros mantenedores não tomem o mapeamento como definitivo.
