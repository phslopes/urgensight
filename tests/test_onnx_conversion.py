"""Testes de conversao e paridade ONNX (Etapa 4).

Cobre scripts/convert_to_onnx.py: converte o pipeline treinado para ONNX e
valida que as predicoes batem com o modelo scikit-learn original. Pulado
automaticamente se as dependencias opcionais do grupo `optimization`
(skl2onnx/onnxruntime) ou o modelo treinado nao estiverem disponiveis --
nao bloqueia `make test`/CI padrao, que roda apenas o grupo `dev`.
"""

import json
from pathlib import Path

import pytest

pytest.importorskip(
    "onnxruntime", reason="onnxruntime nao instalado (grupo opcional 'optimization')"
)
pytest.importorskip(
    "skl2onnx", reason="skl2onnx nao instalado (grupo opcional 'optimization')"
)

from scripts.convert_to_onnx import (  # noqa: E402
    convert_pipeline_to_onnx,
    validate_parity,
)
from src.train import load_pipeline  # noqa: E402

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
def test_conversion_produces_valid_onnx_bytes():
    pipeline = load_pipeline(MODEL_PATH)
    onnx_bytes = convert_pipeline_to_onnx(pipeline)
    assert isinstance(onnx_bytes, bytes)
    assert len(onnx_bytes) > 0


@requires_trained_model
@requires_benchmark_samples
def test_onnx_predictions_match_sklearn_on_benchmark_samples(tmp_path):
    pipeline = load_pipeline(MODEL_PATH)
    onnx_bytes = convert_pipeline_to_onnx(pipeline)
    onnx_path = tmp_path / "model.onnx"
    onnx_path.write_bytes(onnx_bytes)

    samples = json.loads(BENCHMARK_PATH.read_text(encoding="utf-8"))
    report = validate_parity(pipeline, onnx_path, samples)

    assert report["total_samples"] == len(samples)
    # A conversao TF-IDF+LogReg costuma bater 100% nas amostras de
    # benchmark; ver docs/latency_results.md para a analise da pequena
    # divergencia (~0.6%) observada no conjunto de teste completo,
    # concentrada em casos de probabilidade quase empatada (float32 vs
    # float64). Exige-se alta concordancia, nao 100% estrito, para o teste
    # nao ficar fragil a variacoes de versao do onnxruntime/skl2onnx.
    assert report["agreement_rate"] >= 0.95
