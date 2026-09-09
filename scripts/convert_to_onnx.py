"""Converte o pipeline treinado (models/model.pkl) para ONNX Runtime.

Serializa o pipeline TF-IDF + LogisticRegression (ver src/train.py) para o
formato ONNX via `skl2onnx`, permitindo inferencia com `onnxruntime` sem
carregar a stack completa do scikit-learn em runtime. Depois de converter,
valida que as predicoes do modelo ONNX batem com as do pipeline original
sobre as amostras de benchmark (data/benchmark_samples.json) e reporta
eventuais divergencias -- ver docs/latency_results.md para a analise
completa de por que algumas ocorrem (precisao float32 vs float64 em casos
de probabilidade quase empatada, nao erro de conversao).

O artefato models/model.onnx nao e commitado no git (mesmo tratamento de
models/model.pkl -- ver .gitignore e ADR-0006): a conversao e determinista
a partir de um model.pkl fixo, entao e regenerada localmente.

Uso:
    python -m scripts.convert_to_onnx
    python -m scripts.convert_to_onnx --model-path models/model.pkl \
        --onnx-out models/model.onnx

Requer o grupo opcional de dependencias `optimization` (skl2onnx +
onnxruntime): `uv sync --group optimization`.
"""

import argparse
import json
from pathlib import Path

import numpy as np
from skl2onnx import to_onnx
from skl2onnx.common.data_types import StringTensorType

from src.train import load_pipeline

DEFAULT_MODEL_PATH = Path("models/model.pkl")
DEFAULT_ONNX_PATH = Path("models/model.onnx")
DEFAULT_BENCHMARK_PATH = Path("data/benchmark_samples.json")


def convert_pipeline_to_onnx(pipeline) -> bytes:
    """Converte o pipeline sklearn (TF-IDF + classificador) para ONNX.

    `zipmap=False` faz o output `probabilities` vir como tensor denso
    (float32, uma coluna por classe) em vez de uma lista de dicts -- mais
    facil de comparar com `pipeline.predict_proba` e mais rapido de
    desserializar no lado do cliente onnxruntime.
    """
    initial_type = [("text_input", StringTensorType([None, 1]))]
    onnx_model = to_onnx(
        pipeline, initial_types=initial_type, options={"zipmap": False}
    )
    return onnx_model.SerializeToString()


def save_onnx(onnx_bytes: bytes, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(onnx_bytes)


def validate_parity(pipeline, onnx_path: Path, samples: list[dict]) -> dict:
    """Compara predicoes do pipeline original com as do modelo ONNX.

    Roda ambos sobre o mesmo conjunto de textos e retorna um relatorio com
    taxa de concordancia e as divergencias encontradas (texto, classe
    prevista por cada modelo e a probabilidade top-2 do modelo original,
    para diferenciar "erro de conversao" de "caso proximo do limiar de
    decisao").
    """
    import onnxruntime as ort

    texts = [s["text"] for s in samples]

    sklearn_preds = list(pipeline.predict(texts))
    sklearn_proba = pipeline.predict_proba(texts)
    classes = list(pipeline.named_steps["clf"].classes_)

    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name
    onnx_input = np.array(texts, dtype=object).reshape(-1, 1)
    onnx_preds = list(session.run(None, {input_name: onnx_input})[0])

    mismatches = []
    for text, sk_pred, onnx_pred, proba in zip(
        texts, sklearn_preds, onnx_preds, sklearn_proba, strict=True
    ):
        if sk_pred != onnx_pred:
            top2 = sorted(zip(classes, proba, strict=True), key=lambda x: -x[1])[:2]
            mismatches.append(
                {
                    "text": text[:80],
                    "sklearn_prediction": sk_pred,
                    "onnx_prediction": onnx_pred,
                    "top2_probabilities": [(c, round(float(p), 4)) for c, p in top2],
                }
            )

    total = len(texts)
    matches = total - len(mismatches)
    return {
        "total_samples": total,
        "matches": matches,
        "mismatches": mismatches,
        "agreement_rate": matches / total if total else 0.0,
    }


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--onnx-out", type=Path, default=DEFAULT_ONNX_PATH)
    parser.add_argument("--benchmark-path", type=Path, default=DEFAULT_BENCHMARK_PATH)
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Pula a validacao de paridade contra as amostras de benchmark.",
    )
    return parser.parse_args(argv)


def main(argv=None) -> None:
    args = parse_args(argv)

    print(f"Carregando pipeline treinado: {args.model_path}")
    pipeline = load_pipeline(args.model_path)

    print("Convertendo para ONNX...")
    onnx_bytes = convert_pipeline_to_onnx(pipeline)
    save_onnx(onnx_bytes, args.onnx_out)
    print(f"Modelo ONNX salvo em {args.onnx_out} ({len(onnx_bytes) / 1024:.1f} KB)")

    if args.skip_validation:
        return

    if not args.benchmark_path.exists():
        print(f"Aviso: {args.benchmark_path} nao encontrado -- validacao pulada.")
        return

    samples = json.loads(args.benchmark_path.read_text(encoding="utf-8"))
    print(f"Validando paridade de predicoes sobre {len(samples)} amostras...")
    report = validate_parity(pipeline, args.onnx_out, samples)
    print(
        f"Concordancia: {report['matches']}/{report['total_samples']} "
        f"({report['agreement_rate']:.2%})"
    )
    for m in report["mismatches"]:
        print(
            f"  Divergencia: sklearn={m['sklearn_prediction']!r} "
            f"onnx={m['onnx_prediction']!r} top2={m['top2_probabilities']} "
            f"texto={m['text']!r}"
        )


if __name__ == "__main__":
    main()
