# ADR-0009 — Inglês como contrato efetivo de idioma da API

- **Status:** Aceito
- **Data:** 2026-09-02
- **Contexto da decisão:** validação pós-Etapa 3 — bateria de testes manuais via `curl` contra `POST /predict`

## Contexto

O UrgenSight é descrito, em toda a documentação de domínio (`CLAUDE.md`,
README, docstrings de `src/app.py`), como um classificador de **laudos
médicos em português**. Até esta validação, o exemplo interativo do Swagger
(`json_schema_extra.example` de `PredictRequest.text`) reforçava essa
expectativa com um texto em PT-BR (`"Paciente apresenta dor toracica intensa
e dispneia."`).

Uma bateria de testes via `curl` contra `POST /predict` (rodando o modelo
real, `models/model.pkl`) revelou que essa expectativa não corresponde ao
comportamento real do modelo:

| Texto enviado | Idioma | Predição |
|---|---|---|
| `"Paciente apresenta dor toracica intensa e dispneia."` | PT-BR | `normal` |
| `"Paciente do sexo feminino, 45 anos, com dor toracica intensa, dispneia e sudorese fria. Suspeita de infarto agudo do miocardio."` | PT-BR | `normal` |
| `"Severe chest pain with dyspnea and diaphoresis, ECG shows ST elevation, suspect acute myocardial infarction."` | EN | `urgente` |

A causa raiz é conhecida e esperada, não um bug: conforme
[ADR-0001](0001-mapeamento-proxy-do-dataset.md), o dataset de treino
(**Medical Abstracts TC Corpus**) é integralmente em inglês. O
`TfidfVectorizer` do pipeline (`src/train.py`) aprende seu vocabulário
exclusivamente a partir desse corpus; um texto em português produz um vetor
TF-IDF quase inteiramente nulo (poucas ou nenhuma palavra do vocabulário
aparece), e o classificador tende a prever a classe majoritária/mais
"neutra" do espaço de treino independentemente da gravidade clínica descrita.

Esse comportamento nunca havia sido validado de ponta a ponta via requisição
HTTP real — os testes automatizados (`tests/test_app.py`) usam textos curtos
e não avaliam a predição semântica, apenas o contrato HTTP (`prediction` é um
dos três valores válidos do Enum).

## Decisão

Documentar explicitamente **inglês** como o idioma efetivo esperado pela
API, em vez de deixar a suposição de "laudo em português" implícita e
incorreta se propagar pela documentação:

1. O exemplo do Swagger (`src/app.py`) passa a usar um texto em inglês que
   reflete o comportamento real do modelo, alinhado ao exemplo já usado em
   `docs/api_contract.md` e no README.
2. `docs/api_contract.md` e `docs/dataset.md` ganham uma nota explícita sobre
   a limitação de idioma, com o achado empírico registrado.
3. Não alteramos o pipeline de treino nem tentamos mitigar a limitação agora
   (ex.: tradução automática do input, dataset bilíngue) — isso fica como
   direção futura, não como parte desta decisão.

## Alternativas consideradas

**Traduzir o input para inglês antes da inferência** (ex.: via biblioteca de
tradução automática). Rejeitada por ora: adiciona uma dependência externa e
uma etapa de pipeline não trivial (latência, qualidade de tradução médica)
para um projeto de escopo acadêmico; também mascararia o problema em vez de
deixá-lo visível para quem avalia o projeto.

**Buscar/gerar um dataset de treino em português.** Rejeitada por ora pelos
mesmos motivos já registrados em ADR-0001 para a busca de um dataset de
triagem real: datasets médicos rotulados em português, públicos e com volume
suficiente para TF-IDF, não estavam disponíveis dentro do prazo do Tech
Challenge. Permanece como direção legítima de evolução.

**Adicionar um guard de detecção de idioma** que rejeita ou avisa quando o
texto não está em inglês (ex.: `422` com mensagem explicativa). Considerada
mais promissora que as duas anteriores, mas fora do escopo desta validação —
fica registrada aqui como candidata a uma iteração futura, não implementada
agora para não misturar uma mudança de comportamento de API com uma correção
de documentação.

## Consequências

- Quem interage com a API via Swagger UI agora vê, de imediato, um exemplo
  que reflete o comportamento real do modelo (`urgente` em vez de um
  `normal` inesperado para um texto que soa grave).
- A limitação de idioma é rastreável a partir de três pontos de entrada
  (`src/app.py`, `docs/api_contract.md`, `docs/dataset.md`), todos apontando
  para este ADR.
- Toda a documentação e todos os exemplos que ainda usam texto em PT-BR fora
  do escopo desta validação (ex.: `README.md` na seção de benchmark de
  latência com `hey`, `scripts/generate_load.py::FALLBACK_TEXTS`) continuam
  funcionando — o idioma não afeta a validade HTTP do payload, apenas a
  qualidade semântica da predição — mas não foram auditados nem alterados
  por este ADR.
- Uma futura mudança de comportamento (guard de idioma, tradução, ou
  retreino com dataset PT-BR) deve referenciar este ADR e, se aceita,
  atualizar seu Status para `Substituído`.
