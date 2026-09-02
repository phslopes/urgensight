"""DAG de retreino do modelo de triagem de laudos medicos.

Simula um fluxo de retreino agendado com 3 tasks, nessa ordem obrigatoria:
    carregamento/validacao dos dados -> treino -> salvamento do modelo

Reutiliza diretamente as funcoes de src/prepare_dataset.py e src/train.py
(nenhuma logica de treino e duplicada aqui).
"""

import os
import shutil
from datetime import UTC, datetime
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
    def _run_dvc(*args: str) -> None:
        """Executa um comando dvc na raiz do projeto, propagando a falha."""
        import subprocess

        result = subprocess.run(
            ["dvc", *args],
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True,
        )
        print(result.stdout)
        if result.returncode != 0:
            print(result.stderr)
            raise RuntimeError(
                f"dvc {' '.join(args)} falhou (codigo {result.returncode})"
            )

    @task
    def load_and_validate_data() -> dict:
        """Reproduz o estagio de preparacao (arrasta o download se preciso).

        A validacao de colunas continua sendo feita por src/train.py dentro
        do estagio; aqui garantimos que data/processed esta atualizado em
        relacao a data/raw e aos params de prepare.
        """
        _run_dvc("repro", "prepare")

        from src.train import load_dataset, validate_columns

        train_path = DATA_DIR / "processed" / "train.csv"
        test_path = DATA_DIR / "processed" / "test.csv"
        for path in (train_path, test_path):
            validate_columns(load_dataset(path))

        print(f"Dataset validado: {train_path.name}, {test_path.name}")
        return {"train_path": str(train_path), "test_path": str(test_path)}

    @task
    def train_model(data_info: dict) -> dict:
        """Reproduz o estagio de treino. Hiperparametros vem de params.yaml."""
        import json

        _run_dvc("repro", "train")

        metrics_path = DOCS_DIR / "model_metrics.json"
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))

        print(
            f"Treino concluido: accuracy={metrics['accuracy']:.4f}, "
            f"macro_f1={metrics['macro_f1']:.4f}"
        )
        return {
            "model_path": str(MODELS_DIR / "model.pkl"),
            "accuracy": metrics["accuracy"],
            "macro_f1": metrics["macro_f1"],
        }

    @task
    def save_model(train_result: dict) -> None:
        """Publica o modelo no remote do DVC e guarda o historico local."""
        model_path = Path(train_result["model_path"])
        _run_dvc("push")

        history_dir = MODELS_DIR / "history"
        history_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
        shutil.copyfile(model_path, history_dir / f"model_{timestamp}.pkl")

        print(
            f"Modelo publicado no remote e versionado em dvc.lock "
            f"(accuracy={train_result['accuracy']:.4f}, "
            f"macro_f1={train_result['macro_f1']:.4f})"
        )

    data_info = load_and_validate_data()
    train_result = train_model(data_info)
    save_model(train_result)


train_pipeline()
