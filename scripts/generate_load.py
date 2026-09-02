"""Gerador de trafego sintetico para popular os paineis do Grafana (Etapa 3).

Envia requisicoes ao endpoint /predict a uma taxa configuravel. Uma fracao
delas usa payload invalido de proposito (--error-rate), porque a API saudavel
tem taxa de erro zero e um painel de erro vazio nao demonstra observabilidade
nenhuma. Este e trafego de teste deliberado, nao simulacao de falha real.

Uso:
    python scripts/generate_load.py --duration 120 --rps 20 --error-rate 0.1
"""

import argparse
import json
import random
import time
from pathlib import Path

import requests

BENCHMARK_PATH = Path("data/benchmark_samples.json")

# Usado quando data/benchmark_samples.json nao existe, para o script nao
# depender do dataset preparado.
FALLBACK_TEXTS = [
    "Paciente apresenta dor toracica intensa e dispneia progressiva.",
    "Exame de rotina sem alteracoes dignas de nota.",
    "Massa abdominal palpavel, necessita investigacao complementar.",
    "Quadro de cefaleia persistente com deficit neurologico focal.",
]


def load_texts() -> list[str]:
    """Carrega textos reais do benchmark; cai para o fallback se ausente."""
    if not BENCHMARK_PATH.exists():
        return FALLBACK_TEXTS
    samples = json.loads(BENCHMARK_PATH.read_text(encoding="utf-8"))
    return [s["text"] for s in samples] or FALLBACK_TEXTS


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:8000/predict")
    parser.add_argument("--duration", type=int, default=120, help="segundos")
    parser.add_argument("--rps", type=float, default=20.0, help="requisicoes por segundo")
    parser.add_argument(
        "--error-rate",
        type=float,
        default=0.1,
        help="fracao de payloads invalidos (0.0 a 1.0)",
    )
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args(argv)


def main(argv=None) -> None:
    args = parse_args(argv)
    random.seed(args.seed)
    texts = load_texts()

    interval = 1.0 / args.rps
    deadline = time.time() + args.duration
    sent = ok = errors = 0

    print(
        f"Gerando carga em {args.url} por {args.duration}s "
        f"({args.rps} req/s, {args.error_rate:.0%} invalidas)..."
    )

    while time.time() < deadline:
        if random.random() < args.error_rate:
            # Payload sem o campo obrigatorio "text" -> 422 do Pydantic.
            payload = {"texto_errado": "campo invalido"}
        else:
            payload = {"text": random.choice(texts)}

        try:
            response = requests.post(args.url, json=payload, timeout=5)
            sent += 1
            if response.status_code == 200:
                ok += 1
            else:
                errors += 1
        except requests.RequestException as exc:
            errors += 1
            print(f"Falha de conexao: {exc}")

        time.sleep(interval)

    print(f"Enviadas: {sent} | 200: {ok} | nao-2xx ou falhas: {errors}")


if __name__ == "__main__":
    main()
