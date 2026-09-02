# ADR-0007 — uv com lock único e grupos PEP 735

- **Status:** Aceito
- **Data:** 2026-09-02
- **Contexto da decisão:** Etapa 3 (adendo — DVC/uv/Python)

## Contexto

O projeto declarava dependências em quatro lugares: `pyproject.toml`,
`requirements.txt`, `requirements-dev.txt` e `uv.lock`. O `uv.lock` estava
commitado (498 KB) e **nenhum ambiente o usava** — CI, `Dockerfile` e
`Dockerfile.airflow` instalavam com `pip` a partir dos `requirements*.txt`.

Os comentários em `requirements-dev.txt` documentavam a cicatriz disso: o
pacote inexistente `httpx2` e a ausência de `ruff` passaram despercebidos
localmente e só quebraram no CI.

Mais grave, medido durante o desenho: `numpy` era resolvido como `1.26.4` no
container do Airflow (constraints oficiais), `1.26.x` na API (teto `<2.0` em
`requirements.txt`) e `2.2.6` no `uv.lock`. O modelo é treinado no primeiro
ambiente e desserializado no segundo. E `scipy`, `scikit-learn`, `joblib` e
`threadpoolctl` — usados pelo `TfidfVectorizer` para serializar matrizes
esparsas — **não constam** das constraints do Airflow, ficando livres em cada
ambiente.

## Decisão

`pyproject.toml` + `uv.lock` são a única fonte de verdade. Os
`requirements*.txt` foram removidos. Dependências são declaradas em três
conjuntos:

- `[project.dependencies]` — runtime da API: `fastapi`, `uvicorn[standard]`,
  `pydantic`, `prometheus-client`, `scikit-learn==1.5.1`, `joblib`,
  `numpy==1.26.4`, `pandas==2.1.4`, `requests`, `dill`.
- Grupo `pipeline` — hoje contém **só** `dvc>=3.67`, para uso local
  (`uv run dvc ...`, versionamento de dados). Não entra na imagem da API.
- Grupo `dev` — ferramentas de teste e lint, incluindo `pipeline`.

`numpy==1.26.4` e `pandas==2.1.4` ficam fixados na versão das constraints do
Airflow: o ambiente menos flexível dita o piso.

O `uv` torna-se pré-requisito; o `Makefile` perde o fallback para
`python3`/`python` do sistema.

### Achado durante a implementação: `pandas` e `requests` não saem do runtime da API

A intenção original era excluir `pandas`/`requests` da imagem da API — nenhum
endpoint de `src/app.py` os usa diretamente. Na prática, `src/app.py` importa
`src.train` (para desserializar `models/model.pkl`), que importa `pandas` no
module-level e também importa, no module-level, as constantes
`TARGET_COLUMN`/`TEXT_COLUMN`/`VALID_TARGETS` de `src/prepare_dataset.py` —
que por sua vez importa `requests` no module-level (usado só pela função de
download do dataset bruto, nunca chamada pela API). Essa cadeia de imports de
módulo arrasta os dois pacotes para dentro do processo da API mesmo que ela
nunca chame a funcionalidade de rede/CSV: sem eles instalados, `/health`
responde `503` com `ModuleNotFoundError`.

Por isso `pandas` e `requests` foram promovidos de `dependency-groups.pipeline`
para `[project.dependencies]`. Isso é uma extensão do Risco R2 previsto na
spec original da Etapa 3 (que citava só `pandas`); `requests` foi um achado
adicional durante a implementação da Task 5. O desacoplamento de
`prepare_dataset.py`/`train.py` que eliminaria essa cadeia de imports fica
fora do escopo desta ADR.

### `dvc` na imagem do Airflow: isolado via `uv tool install`

A estratégia original prevista era instalar o grupo `pipeline` inteiro na
imagem do Airflow com `uv export --frozen --no-default-groups --group
pipeline` (gerando um `requirements-pipeline.txt` a partir do `uv.lock`) e
`uv pip install -r <export> --constraint <constraints-airflow>` por cima. Essa
estratégia foi **abandonada**: é estruturalmente quebrada, não um problema de
pin faltante.

`uv export` materializa o `uv.lock` como pins **exatos** (`==`), com hash. As
constraints oficiais do Airflow também são pins exatos. Duas exigências `==`
diferentes para o mesmo pacote, vindas de fontes independentes, só coexistem
se coincidirem por acaso — qualquer divergência é um conflito de resolução
sem solução, não um pacote específico a corrigir. Isso foi confirmado
experimentalmente: mesmo as dependências **base** do projeto (sem `dvc`),
exportadas do lock, conflitavam com as constraints do Airflow em `urllib3`
(`2.7.0` vs `2.0.7`). Adicionalmente, `dvc` tem um conflito **estrutural**
genuíno via `fsspec`: `dvc>=3.67.0` exige `fsspec>=2024.2.0`, e o Airflow
2.9.3 fixa `fsspec==2023.12.2` — isso não se resolve pinando mais uma
transitiva, é uma incompatibilidade real entre as duas ferramentas.

A estratégia final, em vigor em `Dockerfile.airflow`:

- As dependências **base** do projeto são instaladas via `uv pip install`
  com especificadores **soltos** (copiados literalmente de
  `[project.dependencies]`, não exportados do lock) + `--constraint
  <constraints-airflow>` — restaura o comportamento de resolução flexível
  que o antigo `pip install -r requirements.txt --constraint` tinha: sem um
  pin exato do nosso lado para competir, o resolvedor aceita os pins do
  Airflow.
- `dvc` é instalado via `uv tool install "dvc>=3.67"`, **isolado**, sem
  nenhuma constraint — esse comando cria um ambiente próprio do `uv`, que
  nunca compartilha site-packages com o Python do Airflow, eliminando o
  conflito de `fsspec` por construção. Confirmado em runtime: o `fsspec` do
  ambiente Python do Airflow permanece `2023.12.2` (intocado), enquanto o
  `dvc` isolado resolve o `fsspec` que ele mesmo precisa, sem colisão.
- `dvc` continua declarado em `[dependency-groups].pipeline` do
  `pyproject.toml`, usado para desenvolvimento local (`uv run dvc ...`) —
  isso não muda.

## Alternativas consideradas

**Manter o pip e os `requirements*.txt`.** Rejeitada: é o estado que produziu
o bug do `httpx2` e a divergência de `numpy`.

**uv no desenvolvimento, exportando `requirements.txt` para Docker/CI.**
Rejeitada: um arquivo gerado e commitado que ninguém edita à mão é exatamente
o que desatualiza sem ninguém perceber.

**Fixar apenas os pacotes que atravessam a fronteira do pickle.** Rejeitada:
reintroduz "dois ambientes que quase batem", que é a origem do problema.

**Instalar o grupo `pipeline` completo na imagem do Airflow via `uv export` +
`--constraint`.** Rejeitada: conflito estrutural de pins exatos (`uv export`)
contra pins exatos (constraints do Airflow) — demonstrado até nas
dependências base do projeto, sem `dvc` na equação (`urllib3`). Não é uma
lista de pacotes incompleta; é o mecanismo de export que é incompatível com
constraints externas exatas.

**Pinar manualmente cada transitiva conflitante via `constraint-dependencies`
(`aiohttp`/`yarl`, depois `wcwidth`, ...).** Tentada e revertida. Ao aplicar
`constraint-dependencies = ["aiohttp==3.9.5", "yarl==1.9.4"]` em `[tool.uv]`
para resolver o conflito de `yarl` puxado por `dvc`, o build voltou a falhar
imediatamente em um conflito do mesmo tipo, agora em `wcwidth`. É o mesmo
padrão de causa raiz (uma transitiva de `dvc` sem pin de projeto, resolvida
para a versão mais nova do PyPI, colidindo com o pin oficial do Airflow) em
outro pacote — pinar um de cada vez não converge, é sintoma do problema
estrutural do `uv export`, não solução. A tentativa foi revertida via
`git revert` assim que ficou claro o padrão.

## Consequências

- Todos os integrantes precisam instalar o `uv`; o README passa a instruir
  `uv sync` no lugar de `python -m venv` + `pip install`.
- O projeto fica em `pandas 2.1.4` e `numpy 1.26.4`, mais antigos que o
  disponível. Preço aceito por um único ambiente resolvido.
- `pandas` e `requests` permanecem em `[project.dependencies]` (runtime da
  API) por causa da cadeia de imports `src.app -> src.train ->
  src.prepare_dataset` — não pela intenção original de excluí-los. A imagem
  da API ainda encolhe em relação ao estado anterior porque `--no-default-groups`
  exclui os grupos `dev`/`pipeline` (pytest, ruff, httpx, dvc), mas não exclui
  mais `pandas`/`requests`.
- `dvc` nunca compartilha ambiente com o Airflow: é instalado isolado via
  `uv tool install` na imagem do Airflow, e via o grupo `pipeline` (`uv sync
  --group pipeline`) no ambiente de desenvolvimento local.
- Afeta a **ADR-0003**: o job `smoke-train` passa a instalar com `uv sync
  --frozen --no-default-groups --group pipeline`. Como `pandas`, `numpy` e
  `scikit-learn` já estão em `[project.dependencies]`, esse `--group
  pipeline` hoje só acrescenta `dvc`, que o `smoke-train` nem usa — pequena
  ineficiência aceita, não corrigida nesta ADR. A decisão daquela ADR (dummy
  training sobre fixture versionado, sem rede) permanece válida.

### Nota (revisão final da branch): lacuna do `dill`/`joblib`/`scipy`/`threadpoolctl` fechada

O parágrafo de contexto acima já apontava que `scipy`, `scikit-learn`,
`joblib` e `threadpoolctl` não constam das constraints oficiais do Airflow,
ficando livres em cada ambiente — mas a estratégia final de
`Dockerfile.airflow` (especificadores soltos + `--constraint`), descrita
acima, não chegou a fixar nenhum desses quatro pacotes; só copiava o
`>=`/`==` que já estava em `[project.dependencies]` na época (que também não
os fixava). Uma comparação real entre a imagem do Airflow e o `uv.lock`
(revisão final da branch) confirmou que `dill` (`0.3.8` na imagem do
Airflow vs. `0.4.1` no `uv.lock`) e `joblib` (`1.6.0` vs. `1.5.3`) já
haviam divergido de fato; `scipy` e `threadpoolctl` só batiam por
coincidência, sem nenhum pin protegendo isso.

Correção aplicada: `dill==0.3.8` e `joblib==1.5.3` passaram a ser pins
exatos em `[project.dependencies]` (antes eram `>=0.3.8`/`>=1.4.0`), e
`Dockerfile.airflow` passou a instalar os quatro pacotes com os mesmos
valores exatos resolvidos em `uv.lock` (`dill==0.3.8`, `joblib==1.5.3`,
`scipy==1.17.1`, `threadpoolctl==3.6.0`) na lista de especificadores soltos
— `scipy` e `threadpoolctl` continuam sendo apenas dependências transitivas
do `scikit-learn`, não precisam de entrada própria em
`[project.dependencies]` para isso, só de aparecer fixados no
`Dockerfile.airflow` e protegidos pelo teste de coerência (`AIRFLOW_PINNED`
em `tests/test_environment_consistency.py`, que agora cobre os quatro
pacotes contra `uv.lock`, não só `numpy`/`pandas`).
