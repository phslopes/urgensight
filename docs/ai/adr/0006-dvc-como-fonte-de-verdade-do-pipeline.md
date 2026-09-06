# ADR-0006 — DVC como fonte de verdade do pipeline de treino

- **Status:** Aceito
- **Data:** 2026-09-02
- **Contexto da decisão:** Etapa 3 (adendo — DVC/uv/Python)

## Contexto

Os hiperparâmetros do treino viviam em três lugares que podiam divergir sem
que nada quebrasse: `src/train.py` (defaults do `argparse`),
`dags/train_pipeline.py` (`seed = 42` e `model_name="logreg"` literais) e
`.github/workflows/ci.yml` (`--max-features 500`).

O versionamento de modelos era `shutil.copyfile` para
`models/history/model_<timestamp>.pkl`: registrava **quando** o modelo foi
treinado, mas não com quais dados, código ou parâmetros. Não havia como
responder "por que este modelo classificou assim?".

E `data/raw` (17 MB) só existia porque um repositório de terceiros continuava
no ar — `.gitignore` o descreve como "regenerable via
`src/prepare_dataset.py`", o que depende de `raw.githubusercontent.com`.

DVC não pontua na rubrica da Fase 3; a adoção é uma decisão de engenharia.

## Decisão

`dvc.yaml` declara três estágios — `download` → `prepare` → `train` — e
`params.yaml` é a fonte única dos hiperparâmetros. O `dvc.yaml` injeta os
valores na linha de comando, de modo que `src/` permanece agnóstico ao DVC e
o `argparse` continua sendo a interface pública.

O Airflow continua sendo o orquestrador: as tasks `load_and_validate_data` e
`train_model` chamam `dvc repro <stage>` (`prepare` e `train`,
respectivamente — `download` é reproduzido a montante quando necessário), e
`save_model` chama `dvc push` para publicar o artefato no remote. Os três
`task_id` são preservados, mantendo visível na UI a ordem
"carregamento → treino → salvamento" exigida pela rubrica.

Remote local em `.dvcstore/`, dentro do repositório e gitignored.

## Alternativas consideradas

**Manter a lógica de treino dentro da DAG.** Rejeitada: é o estado que produziu
os três conjuntos divergentes de parâmetros.

**DVC substituindo o Airflow (uma única task `dvc repro`).** Rejeitada:
achataria a DAG e arriscaria o critério de orquestração, que vale 15% e exige
as etapas de ingestão e treino visíveis.

**Perfis nomeados no `params.yaml`** (`profiles.ci` / `profiles.prod`).
Rejeitada: cada estágio passaria a depender de campos que não usa,
comprometendo o cálculo de hash do DVC e tornando ambíguo qual perfil gerou o
`dvc.lock`. Variação pontual usa `dvc exp run -S` (validado: reproduz só o
estágio afetado e aplica o resultado ao workspace).

**Quatro estágios** (`preprocess → feature_eng → train → evaluate`, como no
material da Fase 2). Rejeitada: o TF-IDF é um passo do `Pipeline` do
scikit-learn dentro de `src/train.py`, e separá-lo quebraria a serialização —
custo alto para imitar um diagrama.

**Remote em S3/GCS.** Rejeitada: exigiria credenciais e um secret no CI. O
material da Fase 2 aceita "local ou S3".

## Consequências

- A imagem do Airflow ganha `git` e `dvc`, e precisa de
  `safe.directory` configurado (o repo é um volume com uid diferente).
- `.dvcstore/` (remote local) fica no `.gitignore` — existe só na máquina que
  rodou `dvc push`, não é publicado com o repositório. `dvc pull` reaproveita
  esse cache **na mesma máquina** entre execuções, sem re-treinar; não
  elimina a dependência do host de terceiros para o time todo. Um integrante
  que clona o repositório do zero tem um remote local vazio, e o primeiro
  `dvc repro` ainda baixa o corpus original de `raw.githubusercontent.com`
  (estágio `download`).
- `dvc.lock` passa a responder "quais dados + código + parâmetros geraram este
  modelo".
- `models/history/` continua existindo e agora é redundante com o `dvc.lock`;
  removê-lo é decisão separada, adiada para depois da entrega.
- O CI **não** reproduz o pipeline (ver ADR-0003). A consistência entre
  `params.yaml` e `dvc.lock` é verificada por teste da suíte
  (`tests/test_environment_consistency.py`), por parsing de YAML — sem rede,
  sem cache e sem `dvc` instalado no runner.
- Promover `data/raw`/`data/processed` a outs cacheados do DVC exigiu tirar
  os `.gitkeep` que mantinham essas pastas no Git (o DVC não gerencia um
  diretório que o Git já rastreia parcialmente); `src/prepare_dataset.py` já
  cria os diretórios via `mkdir(parents=True, exist_ok=True)`, então isso não
  afeta o uso normal.
