"""Testes de estrutura da DAG dags/train_pipeline.py.

Requer o pacote apache-airflow, que nao roda nativamente no Windows -- por
isso os testes sao pulados automaticamente fora do container/CI Linux onde
o Airflow esta instalado (ver docker-compose.airflow.yml).
"""

import sys
from pathlib import Path

import pytest

airflow = pytest.importorskip("airflow")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "dags"))


@pytest.fixture(scope="module")
def dag():
    from train_pipeline import train_pipeline

    return train_pipeline()


def test_dag_id(dag):
    assert dag.dag_id == "train_pipeline"


def test_dag_has_three_tasks(dag):
    assert set(dag.task_dict.keys()) == {
        "load_and_validate_data",
        "train_model",
        "save_model",
    }


def test_task_order_is_load_then_train_then_save(dag):
    load_task = dag.task_dict["load_and_validate_data"]
    train_task = dag.task_dict["train_model"]
    save_task = dag.task_dict["save_model"]

    assert train_task.task_id in load_task.downstream_task_ids
    assert save_task.task_id in train_task.downstream_task_ids
    assert load_task.upstream_task_ids == set()
    assert save_task.downstream_task_ids == set()


def test_dag_has_no_examples_dependency_and_is_not_paused_by_default(dag):
    assert dag.catchup is False
