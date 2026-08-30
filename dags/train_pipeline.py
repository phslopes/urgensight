"""DAG de retreino do modelo de triagem de laudos medicos.

Simula um fluxo de retreino agendado com 3 tasks, nessa ordem obrigatoria:
    carregamento/validacao dos dados -> treino -> salvamento do modelo

Reutiliza diretamente as funcoes de src/prepare_dataset.py e src/train.py
(nenhuma logica de treino e duplicada aqui).
"""

import os
import shutil
from datetime import datetime
from pathlib import Path

from airflow.decorators import dag, task

PROJECT_DIR = Path(os.environ.get("PROJECT_DIR", "/opt/airflow/project"))
DATA_DIR = PROJECT_DIR / "data"
MODELS_DIR = PROJECT_DIR / "models"
DOCS_DIR = PROJECT_DIR / "docs"

default_args = {
    "owner": "urgensight",
    "retries": 1,
}


@dag(
    dag_id="train_pipeline",
    description="Retreino do modelo de triagem: carregamento -> treino -> salvamento",
    schedule="@weekly",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["urgensight", "ml", "retrain"],
)
def train_pipeline():
    @task
    def load_and_validate_data() -> dict:
        """Carrega e valida o dataset processado na Etapa 1.1."""
        from src.train import load_dataset, validate_columns

        train_path = DATA_DIR / "processed" / "train.csv"
        test_path = DATA_DIR / "processed" / "test.csv"

        train_df = load_dataset(train_path)
        test_df = load_dataset(test_path)
        validate_columns(train_df)
        validate_columns(test_df)

        print(
            f"Dataset validado: treino={len(train_df)} amostras, teste={len(test_df)} amostras"
        )
        return {"train_path": str(train_path), "test_path": str(test_path)}

    @task
    def train_model(data_info: dict) -> dict:
        """Treina e avalia o pipeline, reutilizando a logica de src/train.py."""
        from src.prepare_dataset import TARGET_COLUMN, TEXT_COLUMN
        from src.train import (
            build_pipeline,
            evaluate_pipeline,
            format_metrics_report,
            load_dataset,
            save_pipeline,
        )

        train_df = load_dataset(Path(data_info["train_path"]))
        test_df = load_dataset(Path(data_info["test_path"]))

        seed = 42
        pipeline = build_pipeline(model_name="logreg", seed=seed)
        pipeline.fit(train_df[TEXT_COLUMN], train_df[TARGET_COLUMN])

        metrics = evaluate_pipeline(
            pipeline, test_df[TEXT_COLUMN], test_df[TARGET_COLUMN]
        )
        report = format_metrics_report(
            metrics, config={"model_name": "logreg", "seed": seed}
        )

        staging_path = MODELS_DIR / "model_staging.pkl"
        save_pipeline(pipeline, staging_path)

        DOCS_DIR.mkdir(parents=True, exist_ok=True)
        (DOCS_DIR / "model_metrics.md").write_text(report, encoding="utf-8")

        print(
            f"Treino concluido: accuracy={metrics['accuracy']:.4f}, macro_f1={metrics['macro_f1']:.4f}"
        )
        return {
            "staging_path": str(staging_path),
            "accuracy": metrics["accuracy"],
            "macro_f1": metrics["macro_f1"],
        }

    @task
    def save_model(train_result: dict) -> None:
        """Promove o modelo treinado para models/model.pkl e guarda um historico versionado."""
        staging_path = Path(train_result["staging_path"])
        final_path = MODELS_DIR / "model.pkl"
        shutil.copyfile(staging_path, final_path)

        history_dir = MODELS_DIR / "history"
        history_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
        shutil.copyfile(staging_path, history_dir / f"model_{timestamp}.pkl")

        print(
            f"Modelo promovido para {final_path} "
            f"(accuracy={train_result['accuracy']:.4f}, macro_f1={train_result['macro_f1']:.4f})"
        )

    data_info = load_and_validate_data()
    train_result = train_model(data_info)
    save_model(train_result)


train_pipeline()
