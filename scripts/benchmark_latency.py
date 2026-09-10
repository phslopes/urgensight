"""Benchmark de latencia: modelo original (scikit-learn) vs. otimizado (ONNX).

Mede a latencia de inferencia por requisicao de ambos os backends sobre o
mesmo conjunto de entradas (data/benchmark_samples.json), na mesma maquina
e com o mesmo numero de execucoes -- cada chamada processa um unico texto
por vez, simulando o padrao de uso de POST /predict (uma requisicao = uma
predicao), nao inferencia em lote.

Descarta uma rodada de aquecimento (JIT/caches do interpretador e do
runtime) antes de medir, e a reporta separadamente para nao contaminar a
medicao oficial (Etapa 4, item 4.3).

Uso:
    python -m scripts.benchmark_latency
    python -m scripts.benchmark_latency --iterations 1000 --warmup 100

Requer o grupo opcional de dependencias `optimization` (skl2onnx +
onnxruntime): `uv sync --group optimization`. Requer models/model.onnx
gerado previamente com `python -m scripts.convert_to_onnx`.
"""

import argparse
import json
import statistics
import time
from pathlib import Path

import numpy as np

from src.train import load_pipeline

DEFAULT_MODEL_PATH = Path("models/model.pkl")
DEFAULT_ONNX_PATH = Path("models/model.onnx")
DEFAULT_BENCHMARK_PATH = Path("data/benchmark_samples.json")
DEFAULT_OUTPUT_PATH = Path("docs/latency_results.md")


def load_texts(benchmark_path: Path) -> list[str]:
    samples = json.loads(benchmark_path.read_text(encoding="utf-8"))
    if not samples:
        raise ValueError(f"{benchmark_path} nao contem amostras.")
    return [s["text"] for s in samples]


def _cycle_texts(texts: list[str], n: int) -> list[str]:
    """Repete a lista de textos ciclicamente ate atingir `n` elementos."""
    return [texts[i % len(texts)] for i in range(n)]


def measure_sklearn(pipeline, texts: list[str], n: int, warmup: int) -> dict:
    """Mede latencia por requisicao do pipeline scikit-learn original."""
    warmup_texts = _cycle_texts(texts, warmup)
    for text in warmup_texts:
        pipeline.predict([text])

    run_texts = _cycle_texts(texts, n)
    latencies_ms = []
    for text in run_texts:
        start = time.perf_counter()
        pipeline.predict([text])
        latencies_ms.append((time.perf_counter() - start) * 1000)

    return summarize(latencies_ms)


def measure_onnx(onnx_path: Path, texts: list[str], n: int, warmup: int) -> dict:
    """Mede latencia por requisicao do modelo ONNX (onnxruntime)."""
    import onnxruntime as ort

    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name

    def predict_one(text: str):
        onnx_input = np.array([[text]], dtype=object)
        return session.run(None, {input_name: onnx_input})

    warmup_texts = _cycle_texts(texts, warmup)
    for text in warmup_texts:
        predict_one(text)

    run_texts = _cycle_texts(texts, n)
    latencies_ms = []
    for text in run_texts:
        start = time.perf_counter()
        predict_one(text)
        latencies_ms.append((time.perf_counter() - start) * 1000)

    return summarize(latencies_ms)


def summarize(latencies_ms: list[float]) -> dict:
    ordered = sorted(latencies_ms)
    return {
        "n": len(ordered),
        "mean_ms": statistics.mean(ordered),
        "median_ms": statistics.median(ordered),
        "p95_ms": ordered[int(len(ordered) * 0.95) - 1],
        "min_ms": ordered[0],
        "max_ms": ordered[-1],
    }


def format_report(sklearn_stats: dict, onnx_stats: dict, config: dict) -> str:
    # Normaliza para barra "/" independente do SO (Path.__str__ usa "\" no
    # Windows), ja que este relatorio e commitado e lido no GitHub/README.
    config = {
        **config,
        "benchmark_path": Path(config["benchmark_path"]).as_posix(),
        "model_path": Path(config["model_path"]).as_posix(),
        "onnx_path": Path(config["onnx_path"]).as_posix(),
    }
    improvement_mean = (
        sklearn_stats["mean_ms"] - onnx_stats["mean_ms"]
    ) / sklearn_stats["mean_ms"]
    improvement_p95 = (sklearn_stats["p95_ms"] - onnx_stats["p95_ms"]) / sklearn_stats[
        "p95_ms"
    ]

    def row(label: str, stats: dict) -> str:
        return (
            f"| {label} | {stats['n']} | {stats['mean_ms']:.3f} | "
            f"{stats['median_ms']:.3f} | {stats['p95_ms']:.3f} | "
            f"{stats['min_ms']:.3f} | {stats['max_ms']:.3f} |"
        )

    lines = [
        "# Resultados de Benchmark — Original vs. Otimizado (ONNX Runtime)",
        "",
        "Latencia de inferencia por requisicao (uma predicao por chamada, "
        "sem batching), medida na mesma maquina, sobre o mesmo conjunto de "
        f"entradas (`{config['benchmark_path']}`) e o mesmo numero de "
        "execucoes para os dois backends. Aquecimento (JIT/caches) "
        "descartado e reportado separadamente — ver secao abaixo.",
        "",
        "## Ambiente de execucao",
        "",
        "| Item | Valor |",
        "|------|-------|",
        f"| Iteracoes medidas por backend | {config['iterations']} |",
        f"| Iteracoes de aquecimento (descartadas) | {config['warmup']} |",
        f"| Amostras usadas (cicladas) | {config['sample_count']} de `{config['benchmark_path']}` |",
        f"| Modelo original | `{config['model_path']}` (TF-IDF + LogisticRegression, joblib) |",
        f"| Modelo otimizado | `{config['onnx_path']}` (mesmo pipeline, ONNX Runtime) |",
        "| Tecnica de otimizacao | Conversao para ONNX Runtime (`skl2onnx`) |",
        "",
        "## Resultados comparativos",
        "",
        "| Modelo | N | Media (ms) | Mediana (ms) | p95 (ms) | Min (ms) | Max (ms) |",
        "|---|---|---|---|---|---|---|",
        row("Original (scikit-learn)", sklearn_stats),
        row("Otimizado (ONNX Runtime)", onnx_stats),
        "",
        "## Melhoria de latencia",
        "",
        f"- **Media**: {improvement_mean:+.2%} "
        f"({sklearn_stats['mean_ms']:.3f} ms → {onnx_stats['mean_ms']:.3f} ms)",
        f"- **p95**: {improvement_p95:+.2%} "
        f"({sklearn_stats['p95_ms']:.3f} ms → {onnx_stats['p95_ms']:.3f} ms)",
        "",
        "Valores positivos indicam reducao de latencia (modelo otimizado mais "
        "rapido); valores negativos indicam regressao.",
    ]
    return "\n".join(lines) + "\n"


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--onnx-path", type=Path, default=DEFAULT_ONNX_PATH)
    parser.add_argument("--benchmark-path", type=Path, default=DEFAULT_BENCHMARK_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--iterations", type=int, default=500)
    parser.add_argument("--warmup", type=int, default=50)
    return parser.parse_args(argv)


def main(argv=None) -> None:
    args = parse_args(argv)

    if not args.model_path.exists():
        raise FileNotFoundError(
            f"{args.model_path} nao encontrado. Rode `python -m src.train` antes."
        )
    if not args.onnx_path.exists():
        raise FileNotFoundError(
            f"{args.onnx_path} nao encontrado. Rode "
            "`python -m scripts.convert_to_onnx` antes."
        )

    texts = load_texts(args.benchmark_path)
    print(f"Amostras carregadas: {len(texts)} de {args.benchmark_path}")

    print(f"Carregando pipeline original: {args.model_path}")
    pipeline = load_pipeline(args.model_path)

    print(
        f"Medindo backend original ({args.warmup} aquecimento + "
        f"{args.iterations} medidas)..."
    )
    sklearn_stats = measure_sklearn(pipeline, texts, args.iterations, args.warmup)
    print(
        f"  media={sklearn_stats['mean_ms']:.3f}ms p95={sklearn_stats['p95_ms']:.3f}ms"
    )

    print(
        f"Medindo backend ONNX ({args.warmup} aquecimento + "
        f"{args.iterations} medidas)..."
    )
    onnx_stats = measure_onnx(args.onnx_path, texts, args.iterations, args.warmup)
    print(f"  media={onnx_stats['mean_ms']:.3f}ms p95={onnx_stats['p95_ms']:.3f}ms")

    report = format_report(
        sklearn_stats,
        onnx_stats,
        config={
            "iterations": args.iterations,
            "warmup": args.warmup,
            "sample_count": len(texts),
            "benchmark_path": args.benchmark_path,
            "model_path": args.model_path,
            "onnx_path": args.onnx_path,
        },
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(f"Relatorio salvo em {args.output}")


if __name__ == "__main__":
    main()
