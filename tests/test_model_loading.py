"""Script isolado de validacao do model.pkl serializado.

Carrega models/model.pkl e valida que ele consegue prever as classes de
urgencia para as amostras de benchmark (data/benchmark_samples.json).
Pulado automaticamente se o modelo ainda nao foi treinado (`python -m
src.train`), para nao quebrar um clone limpo do repositorio.
"""
import json
from pathlib import Path

import pytest

from src.prepare_dataset import TARGET_COLUMN, TEXT_COLUMN, VALID_TARGETS
from src.train import load_pipeline

MODEL_PATH = Path("models/model.pkl")
BENCHMARK_PATH = Path("data/benchmark_samples.json")

requires_trained_model = pytest.mark.skipif(
    not MODEL_PATH.exists(),
    reason=f"{MODEL_PATH} nao encontrado -- rode `python -m src.train` antes.",
)
requires_benchmark_samples = pytest.mark.skipif(
    not BENCHMARK_PATH.exists(),
    reason=f"{BENCHMARK_PATH} nao encontrado -- rode `python -m src.prepare_dataset` antes.",
)


@requires_trained_model
def test_model_loads_without_error():
    pipeline = load_pipeline(MODEL_PATH)
    assert pipeline is not None


@requires_trained_model
def test_model_pipeline_has_expected_steps():
    pipeline = load_pipeline(MODEL_PATH)
    step_names = [name for name, _ in pipeline.steps]
    assert step_names == ["tfidf", "clf"]


@requires_trained_model
@requires_benchmark_samples
def test_model_predicts_valid_classes_for_benchmark_samples():
    pipeline = load_pipeline(MODEL_PATH)
    samples = json.loads(BENCHMARK_PATH.read_text(encoding="utf-8"))

    texts = [s[TEXT_COLUMN] for s in samples]
    predictions = pipeline.predict(texts)

    assert len(predictions) == len(texts)
    assert set(predictions) <= VALID_TARGETS


@requires_trained_model
@requires_benchmark_samples
def test_model_accuracy_on_benchmark_is_above_random_baseline():
    pipeline = load_pipeline(MODEL_PATH)
    samples = json.loads(BENCHMARK_PATH.read_text(encoding="utf-8"))

    texts = [s[TEXT_COLUMN] for s in samples]
    expected = [s[TARGET_COLUMN] for s in samples]
    predictions = pipeline.predict(texts)

    accuracy = sum(p == e for p, e in zip(predictions, expected)) / len(expected)
    # 3 classes -> baseline aleatorio ~0.33; exigimos uma folga clara acima disso.
    assert accuracy > 0.5
