# ADR-0011 — Integração opcional do backend ONNX na API

- **Status:** Aceito
- **Data:** 2026-09-09
- **Contexto da decisão:** extensão da Etapa 4 (`feat/etapa-4-otimizacao-latencia`), autorizada pelo Integrante 2 para integrar o `models/model.onnx` em `src/app.py` — item opcional do handoff previsto em [ADR-0010](0010-onnx-runtime-como-tecnica-de-otimizacao.md) e no checklist da Etapa 4 (4.3: "apoiar o Integrante 2 na medição ponta a ponta").

## Contexto

ADR-0010 estabeleceu a técnica de otimização (ONNX Runtime) e deixou a
integração em `src/app.py` fora do escopo — arquivo de propriedade da
Etapa 2. Com autorização explícita do Integrante 2, esta ADR cobre como
essa integração foi feita, mantendo o requisito de não quebrar o
comportamento existente da Etapa 2.

## Decisão

1. **Troca de backend via variável de ambiente**, não uma reescrita do
   endpoint: `MODEL_BACKEND` (`"sklearn"`, padrão, ou `"onnx"`). Ausente
   ou com qualquer valor diferente de `"onnx"`, o comportamento é
   idêntico ao da Etapa 2 — mesmo caminho de carregamento
   (`models/model.pkl` via `joblib`), mesmo contrato de API.
2. **`src/onnx_inference.py`** (novo módulo) define `OnnxPipeline`, uma
   classe fina que adapta uma `onnxruntime.InferenceSession` à mesma
   interface `.predict(texts) -> lista de rótulos` do pipeline
   scikit-learn. `src/app.py` só precisou trocar `_load_model` para
   escolher a classe certa — `/predict`, `/health`, contrato Pydantic e
   métricas Prometheus não mudaram uma linha.
3. **Grupo de dependência `api-onnx`** (`pyproject.toml`), separado do
   `optimization` da ADR-0010: só `onnxruntime`, sem `skl2onnx`/`onnx`.
   Confirmado localmente que `onnxruntime.InferenceSession` não importa o
   pacote `onnx` em runtime — então a imagem da API evita o pin
   `onnx<1.18` (que só existe por causa do conflito `ml-dtypes`/`numpy`
   da *conversão*, não da *inferência*; ver ADR-0010) e fica mais
   enxuta.
4. **`Dockerfile`** passa a instalar o grupo `api-onnx` sempre (custo
   pequeno e constante, ~onnxruntime, mesmo se ninguém ativar o backend)
   e copia `models/model.onnx` de forma **condicional**: `COPY
   models/model.onn[x] ./models/` — o colchete é o idiom padrão do
   Docker para "copiar se existir" (não existe `COPY --if-exists`
   nativo). Sem `model.onnx` gerado localmente
   (`make convert-onnx`), o build da imagem continua funcionando
   normalmente, só não inclui o artefato ONNX.
5. **`docker-compose.yml`** ganha `MODEL_BACKEND: ${MODEL_BACKEND:-sklearn}`
   no serviço `api` — o padrão do Compose continua sendo o backend da
   Etapa 2; `MODEL_BACKEND=onnx docker compose up` ativa o otimizado.

## Bug encontrado e corrigido: locale ausente na imagem

Testando o backend ONNX dentro do container (não reproduzia localmente,
fora do Docker), `POST /predict` retornava `503` com o log:

```
[ONNXRuntimeError] : 1 : FAIL : Exception during initialization:
.../string_normalizer.cc:235 ... Failed to construct locale with
name:en_US.UTF-8:locale::facet::_S_create_c_locale name not valid:
Please, install necessary language-pack-XX and configure locales
```

Causa: o nó `StringNormalizer` que o `skl2onnx` gera para o
`TfidfVectorizer` inicializa um `std::locale("en_US.UTF-8")` dentro do
ONNX Runtime (C++). A imagem base `python:3.12-slim` só tem os locales
`C`/`POSIX` instalados. Corrigido no `Dockerfile`: instala o pacote
`locales`, gera `en_US.UTF-8` via `locale-gen` e define
`LANG`/`LANGUAGE`/`LC_ALL`. Validado após a correção: `/health` fica
`healthy` e `/predict` responde `200` com o backend ONNX.

Isso não afeta o backend `sklearn` (padrão) nem foi percebido nos testes
locais (`scripts/convert_to_onnx.py`, `scripts/benchmark_latency.py`,
`tests/test_app_onnx_backend.py`) porque todos rodam no host (Windows),
não dentro da imagem `python:3.12-slim` — reforça por que a etapa "medir
ponta a ponta em Docker" (checklist 4.3) tem valor além do benchmark
local.

## Resultados medidos em Docker (ponta a ponta)

Sem `hey`/`ab` disponíveis neste ambiente, a medição usou um cliente
Python equivalente (`requests`, sequencial, mesmo payload, aquecimento
descartado) contra o container já em execução — mesma máquina para as
duas rodadas (sklearn vs. onnx), mas **não** a mesma máquina/metodologia
do baseline oficial em `docs/baseline_latency.md` (macOS M4, `hey -c 10`).

| Backend | N | Média (ms) | Mediana (ms) | p95 (ms) |
|---|---|---|---|---|
| sklearn (padrão, container) | 300 | ~16.4 | ~15.8 | ~28.9 |
| onnx (container) | 300 | ~15.1 | ~15.8 | ~27.6 |

(Média de duas rodadas cada; valores individuais em
`docs/latency_results.md`.)

**O ganho ponta a ponta (~5-12%) é bem menor que o ganho medido no
modelo puro (~68%, ADR-0010).** Não é regressão nem erro de medição: a
requisição HTTP tem overhead (parsing, validação Pydantic, rede,
serialização de resposta) que não muda com a troca de backend do
modelo — e nesse payload pequeno, esse overhead domina o tempo total.
O ambiente desta medição (Docker Desktop no Windows, WSL2/Hyper-V,
cliente sequencial em Python) tem overhead de rede sensivelmente maior
que o baseline original (macOS nativo, `hey` com 10 conexões
concorrentes) — por isso os números absolutos aqui (~15-16ms) não são
comparáveis linha a linha com `docs/baseline_latency.md` (~2-6ms). A
comparação válida desta ADR é sklearn vs. onnx **dentro do mesmo
ambiente**, não contra o baseline histórico.

## Alternativas consideradas

**Trocar o backend padrão para ONNX.** Rejeitada: o ganho ponta a ponta
medido é pequeno e o backend sklearn é o caminho validado e testado
desde a Etapa 2. Manter `sklearn` como padrão preserva o comportamento
já validado; `onnx` fica como opt-in para quem quiser demonstrar/usar.

**Fazer o toggle de backend em runtime (por requisição, via header) em
vez de na inicialização.** Rejeitada por complexidade desnecessária: o
checklist pede comparação de configurações, não um endpoint que sirva
os dois modelos simultaneamente.

## Consequências

- `src/app.py` ganha uma bifurcação pequena e isolada (`MODEL_BACKEND`);
  o contrato HTTP, os testes existentes (`tests/test_app.py`) e o
  comportamento padrão não mudam.
- A imagem Docker cresce (`onnxruntime` + pacote `locales`) mesmo para
  quem nunca usa `MODEL_BACKEND=onnx` — custo aceito em troca do toggle
  funcionar "out of the box" sem exigir uma imagem separada.
- Sem `models/model.onnx` gerado antes do build (`make convert-onnx`),
  `MODEL_BACKEND=onnx` degrada para `503` (mesmo padrão já usado para
  modelo ausente/inválido, Etapa 2) — não derruba a API.
- O número "ponta a ponta" desta ADR não substitui uma remedição formal
  com `hey`, na mesma máquina do baseline original — fica como
  refinamento futuro se o grupo quiser um número diretamente comparável
  a `docs/baseline_latency.md`.
