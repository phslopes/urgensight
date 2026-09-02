"""Treino do modelo baseline de triagem de laudos medicos.

Carrega o dataset processado (data/processed/train.csv e test.csv), treina
um pipeline TF-IDF + classificador leve (Logistic Regression ou Linear SVC),
avalia accuracy e F1 por classe, salva as metricas em docs/model_metrics.md
e serializa o pipeline completo em models/model.pkl.

Uso:
    python -m src.train --train-path data/processed/train.csv \
        --test-path data/processed/test.csv --model logreg
"""

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

from src.prepare_dataset import TARGET_COLUMN, TEXT_COLUMN, VALID_TARGETS

MODEL_BUILDERS = {
    "logreg": lambda seed: LogisticRegression(
        max_iter=1000, class_weight="balanced", random_state=seed
    ),
    "linear_svc": lambda seed: LinearSVC(class_weight="balanced", random_state=seed),
}


def load_dataset(path: Path) -> pd.DataFrame:
    """Carrega um CSV processado (colunas text/target)."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {path}")
    return pd.read_csv(path)


def validate_columns(df: pd.DataFrame) -> None:
    """Valida que o DataFrame possui as colunas e valores esperados."""
    required = {TEXT_COLUMN, TARGET_COLUMN}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Colunas obrigatorias ausentes: {sorted(missing)}")

    if len(df) == 0:
        raise ValueError("Dataset vazio.")

    unknown_targets = set(df[TARGET_COLUMN].unique()) - VALID_TARGETS
    if unknown_targets:
        raise ValueError(f"Valores de target desconhecidos: {sorted(unknown_targets)}")


def build_pipeline(model_name: str, seed: int, max_features: int = 20000) -> Pipeline:
    """Monta o pipeline TF-IDF + classificador leve."""
    if model_name not in MODEL_BUILDERS:
        raise ValueError(
            f"Modelo desconhecido: {model_name!r}. Opcoes: {sorted(MODEL_BUILDERS)}"
        )

    vectorizer = TfidfVectorizer(
        max_features=max_features,
        ngram_range=(1, 2),
        min_df=2,
        stop_words="english",
    )
    classifier = MODEL_BUILDERS[model_name](seed)

    return Pipeline(steps=[("tfidf", vectorizer), ("clf", classifier)])


def evaluate_pipeline(pipeline: Pipeline, X_test, y_test) -> dict:
    """Avalia o pipeline treinado: accuracy, F1 macro e F1 por classe."""
    predictions = pipeline.predict(X_test)

    labels = sorted(VALID_TARGETS)
    report = classification_report(
        y_test, predictions, labels=labels, output_dict=True, zero_division=0
    )
    matrix = confusion_matrix(y_test, predictions, labels=labels)

    return {
        "accuracy": accuracy_score(y_test, predictions),
        "macro_f1": report["macro avg"]["f1-score"],
        "weighted_f1": report["weighted avg"]["f1-score"],
        "per_class": {target: report[target] for target in labels},
        "confusion_matrix": {"labels": labels, "matrix": matrix.tolist()},
    }


def format_metrics_report(metrics: dict, config: dict) -> str:
    """Formata as metricas de avaliacao como um relatorio Markdown."""
    lines = [
        "# Metricas do Modelo Baseline",
        "",
        "## Configuracao",
        f"- Modelo: `{config['model_name']}`",
        f"- Seed: `{config['seed']}`",
        "",
        "## Resultados gerais",
        f"- **Accuracy**: {metrics['accuracy']:.4f}",
        f"- **Macro F1**: {metrics['macro_f1']:.4f}",
        f"- **Weighted F1**: {metrics['weighted_f1']:.4f}",
        "",
        "## F1-score por classe",
        "",
        "| Classe | Precision | Recall | F1-score | Suporte |",
        "|---|---|---|---|---|",
    ]
    for target in sorted(VALID_TARGETS):
        stats = metrics["per_class"][target]
        lines.append(
            f"| {target} | {stats['precision']:.4f} | {stats['recall']:.4f} "
            f"| {stats['f1-score']:.4f} | {int(stats['support'])} |"
        )

    cm = metrics["confusion_matrix"]
    lines += [
        "",
        "## Matriz de confusao",
        "",
        "Linhas = classe real, colunas = classe prevista.",
        "",
        "| | " + " | ".join(cm["labels"]) + " |",
        "|---|" + "---|" * len(cm["labels"]),
    ]
    for label, row in zip(cm["labels"], cm["matrix"], strict=False):
        lines.append(f"| **{label}** | " + " | ".join(str(v) for v in row) + " |")

    lines += [
        "",
        "## Compatibilidade com ONNX (nota para Integrante 4)",
        "",
        "O pipeline usa `TfidfVectorizer` + `LogisticRegression`/`LinearSVC`, "
        "ambos suportados pelo conversor [`sklearn-onnx`](https://github.com/onnx/sklearn-onnx). "
        "Conversao preliminar esperada sem obstaculos. Caso a conversao para ONNX "
        "nao seja viavel, o plano alternativo e manter a inferencia via "
        "`joblib`/scikit-learn diretamente (pipeline ja leve, sem necessidade de GPU).",
    ]

    return "\n".join(lines) + "\n"


def format_metrics_json(metrics: dict, config: dict) -> dict:
    """Achata as metricas em escalares para `dvc metrics show/diff`.

    O relatorio Markdown continua sendo a evidencia legivel da entrega; este
    JSON existe para que o DVC consiga comparar runs entre commits.
    """
    payload = {
        "model": config["model_name"],
        "seed": config["seed"],
        "accuracy": round(float(metrics["accuracy"]), 4),
        "macro_f1": round(float(metrics["macro_f1"]), 4),
        "weighted_f1": round(float(metrics["weighted_f1"]), 4),
    }
    for target in sorted(VALID_TARGETS):
        payload[f"f1_{target}"] = round(
            float(metrics["per_class"][target]["f1-score"]), 4
        )
    return payload


def save_pipeline(pipeline: Pipeline, path: Path) -> None:
    """Serializa o pipeline completo (vetorizador + modelo) via joblib."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, path)


def load_pipeline(path: Path) -> Pipeline:
    """Carrega um pipeline serializado via joblib."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Modelo nao encontrado: {path}")
    return joblib.load(path)


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--train-path", type=Path, default=Path("data/processed/train.csv")
    )
    parser.add_argument(
        "--test-path", type=Path, default=Path("data/processed/test.csv")
    )
    parser.add_argument("--model-out", type=Path, default=Path("models/model.pkl"))
    parser.add_argument(
        "--metrics-out", type=Path, default=Path("docs/model_metrics.md")
    )
    parser.add_argument(
        "--metrics-json-out", type=Path, default=Path("docs/model_metrics.json")
    )
    parser.add_argument("--model", choices=sorted(MODEL_BUILDERS), default="logreg")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-features", type=int, default=20000)
    return parser.parse_args(argv)


def main(argv=None) -> None:
    args = parse_args(argv)
    np.random.seed(args.seed)

    print(f"Carregando dataset de treino: {args.train_path}")
    train_df = load_dataset(args.train_path)
    validate_columns(train_df)

    print(f"Carregando dataset de teste: {args.test_path}")
    test_df = load_dataset(args.test_path)
    validate_columns(test_df)

    print(f"Treinando modelo '{args.model}' (seed={args.seed})...")
    pipeline = build_pipeline(
        args.model, seed=args.seed, max_features=args.max_features
    )
    pipeline.fit(train_df[TEXT_COLUMN], train_df[TARGET_COLUMN])

    print("Avaliando modelo no conjunto de teste...")
    metrics = evaluate_pipeline(pipeline, test_df[TEXT_COLUMN], test_df[TARGET_COLUMN])
    print(f"Accuracy: {metrics['accuracy']:.4f} | Macro F1: {metrics['macro_f1']:.4f}")

    report = format_metrics_report(
        metrics, config={"model_name": args.model, "seed": args.seed}
    )
    args.metrics_out.parent.mkdir(parents=True, exist_ok=True)
    args.metrics_out.write_text(report, encoding="utf-8")
    print(f"Metricas salvas em {args.metrics_out}")

    payload = format_metrics_json(
        metrics, config={"model_name": args.model, "seed": args.seed}
    )
    args.metrics_json_out.parent.mkdir(parents=True, exist_ok=True)
    args.metrics_json_out.write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Metricas (JSON) salvas em {args.metrics_json_out}")

    save_pipeline(pipeline, args.model_out)
    print(f"Pipeline salvo em {args.model_out}")


if __name__ == "__main__":
    main()
