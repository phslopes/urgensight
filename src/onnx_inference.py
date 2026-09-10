"""Backend de inferencia via ONNX Runtime (Etapa 4).

Adapta uma ``onnxruntime.InferenceSession`` sobre ``models/model.onnx``
(gerado por ``scripts/convert_to_onnx.py``) a mesma interface
``.predict(texts) -> lista de rotulos`` exposta pelo pipeline
scikit-learn (ver ``src/train.py``), para que ``src/app.py`` troque de
backend sem alterar o codigo do endpoint ``/predict``.

Ver ``docs/latency_results.md`` para o benchmark comparativo e
``docs/ai/adr/0010-onnx-runtime-como-tecnica-de-otimizacao.md`` /
``0011-integracao-opcional-do-onnx-na-api.md`` para as decisoes por
tras desta classe.
"""

from pathlib import Path

import numpy as np


class OnnxPipeline:
    """Pipeline de inferencia via ONNX Runtime com a interface do sklearn."""

    def __init__(self, onnx_path: Path):
        import onnxruntime as ort

        onnx_path = Path(onnx_path)
        if not onnx_path.exists():
            raise FileNotFoundError(f"Modelo ONNX nao encontrado: {onnx_path}")

        self._session = ort.InferenceSession(
            str(onnx_path), providers=["CPUExecutionProvider"]
        )
        self._input_name = self._session.get_inputs()[0].name

    def predict(self, texts: list[str]) -> list[str]:
        onnx_input = np.array(texts, dtype=object).reshape(-1, 1)
        labels = self._session.run(None, {self._input_name: onnx_input})[0]
        return list(labels)
