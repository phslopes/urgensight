# Metricas do Modelo Baseline

## Configuracao
- Modelo: `logreg`
- Seed: `42`

## Resultados gerais
- **Accuracy**: 0.7685
- **Macro F1**: 0.7718
- **Weighted F1**: 0.7675

## F1-score por classe

| Classe | Precision | Recall | F1-score | Suporte |
|---|---|---|---|---|
| atencao | 0.7709 | 0.8000 | 0.7852 | 820 |
| normal | 0.7779 | 0.7051 | 0.7397 | 929 |
| urgente | 0.7505 | 0.8350 | 0.7905 | 497 |

## Matriz de confusao

Linhas = classe real, colunas = classe prevista.

| | atencao | normal | urgente |
|---|---|---|---|
| **atencao** | 656 | 129 | 35 |
| **normal** | 171 | 655 | 103 |
| **urgente** | 24 | 58 | 415 |

## Compatibilidade com ONNX (nota para Integrante 4)

O pipeline usa `TfidfVectorizer` + `LogisticRegression`/`LinearSVC`, ambos suportados pelo conversor [`sklearn-onnx`](https://github.com/onnx/sklearn-onnx). Conversao preliminar esperada sem obstaculos. Caso a conversao para ONNX nao seja viavel, o plano alternativo e manter a inferencia via `joblib`/scikit-learn diretamente (pipeline ja leve, sem necessidade de GPU).
