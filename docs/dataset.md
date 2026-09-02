# Dataset — Fonte, Formato e Mapeamento de Classes

## Fonte

**Medical Abstracts TC Corpus** ([sebischair/Medical-Abstracts-TC-Corpus](https://github.com/sebischair/Medical-Abstracts-TC-Corpus)),
um corpus público de 14.438 resumos (abstracts) de literatura médica, cada um
rotulado com uma das 5 categorias clínicas abaixo. Publicado para pesquisa em
classificação de texto médico (NLPIR 2022 / Schopf et al.).

Os arquivos originais (`medical_tc_train.csv`, `medical_tc_test.csv`) são
baixados automaticamente pelo script `src/prepare_dataset.py` diretamente do
GitHub e salvos em `data/raw/` (não versionados — ver `.gitignore`).

Caminho recomendado para obter os dados: `uv run dvc pull` (ver
[ADR-0006](ai/adr/0006-dvc-como-fonte-de-verdade-do-pipeline.md)) — baixa
`data/raw` já processado do remote local do DVC, sem depender do GitHub de
terceiros. O download direto via `src/prepare_dataset.py` continua
funcionando como fallback (ex.: primeira execução, antes de qualquer
`dvc push`).

## Formato original

| Coluna | Descrição |
|---|---|
| `condition_label` | Inteiro de 1 a 5 indicando a categoria clínica |
| `medical_abstract` | Texto do resumo médico |

Categorias originais:

| Label | Categoria |
|---|---|
| 1 | Neoplasms (neoplasias) |
| 2 | Digestive system diseases |
| 3 | Nervous system diseases |
| 4 | Cardiovascular diseases |
| 5 | General pathological conditions |

## Mapeamento para as classes do projeto

O corpus **não** possui rótulos de urgência/triagem — os rótulos descrevem a
categoria clínica do texto, não a gravidade do caso. Para viabilizar o
projeto (que exige classificação em `normal`, `atencao`, `urgente`),
adotamos um mapeamento **proxy**, baseado em um critério simples de
severidade clínica típica de cada categoria:

| Categoria original | Classe do projeto | Justificativa |
|---|---|---|
| Cardiovascular diseases (4) | **urgente** | Eventos cardiovasculares (ex.: infarto, arritmias) tipicamente exigem resposta imediata |
| Neoplasms (1) | **atencao** | Achados oncológicos requerem investigação e acompanhamento especializado, mas não são necessariamente uma emergência imediata |
| Nervous system diseases (3) | **atencao** | Condições neurológicas geralmente requerem avaliação especializada e monitoramento |
| Digestive system diseases (2) | **normal** | Predominantemente queixas/condições de rotina no corpus |
| General pathological conditions (5) | **normal** | Categoria genérica de condições de rotina |

> **Limitação conhecida:** este é um mapeamento didático/proxy para fins
> acadêmicos, não uma classificação clínica de triagem real (ex.: Manchester
> Protocol). Ele foi escolhido por produzir uma distribuição de classes
> plausível (mais casos rotineiros que urgentes) e por usar um dataset
> público, real e verificável — em vez de rótulos sintéticos artificiais.
> Qualquer uso além do escopo acadêmico deste projeto exigiria revisão por
> profissionais de saúde e um dataset com rótulos de urgência reais.

## Esquema final (após `src/prepare_dataset.py`)

| Coluna | Descrição |
|---|---|
| `text` | Texto do laudo/resumo médico |
| `target` | Classe de urgência: `normal`, `atencao` ou `urgente` |

## Limpeza aplicada

- Remoção de registros com rótulo nulo
- Remoção de registros com texto nulo ou em branco
- Remoção de duplicatas exatas de texto
- Normalização de espaços em branco (strip)

Resultado: **11.227 amostras válidas** (dataset bruto tinha 14.438; ver
`docs/dataset_distribution.md` para o relatório completo, gerado
automaticamente a cada execução do script).

## Split e reprodutibilidade

- Split treino/teste: 80/20, estratificado por classe (`target`)
- Seed fixa: `42` (parametrizável via `--seed`)
- Saídas: `data/processed/train.csv`, `data/processed/test.csv`
- Amostras de benchmark (15 por classe, 45 no total): `data/benchmark_samples.json`

## Como reproduzir

```bash
python -m src.prepare_dataset --seed 42 --test-size 0.2 --benchmark-per-class 15
```

Ver instruções completas de instalação e execução no [README.md](../README.md).
