# Dockerfile da API de inferencia (Etapa 2) -- UrgenSight.
# Nao confundir com Dockerfile.airflow (orquestracao Airflow, Etapa 1.3).
#
# Build:  docker build -t urgensight-api .
# Run:    docker run -d -p 8000:8000 --name urgensight-api urgensight-api
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Locale en_US.UTF-8 (Etapa 4/ADR-0011): o no StringNormalizer que o
# skl2onnx gera para o TfidfVectorizer inicializa um std::locale("en_US.UTF-8")
# no onnxruntime -- ausente por padrao no python:3.12-slim (so tem "C"/"POSIX"),
# o que faz a InferenceSession falhar no startup com MODEL_BACKEND=onnx
# (erro so aparece em runtime, dentro do container, nao no build local).
RUN apt-get update \
    && apt-get install -y --no-install-recommends locales \
    && sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen \
    && locale-gen \
    && rm -rf /var/lib/apt/lists/*
ENV LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    LC_ALL=en_US.UTF-8

# Usuario nao-root para execucao da API.
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

WORKDIR /app

# uv: instalador unico do projeto (ver ADR-0007). Versao fixada para que o
# build seja reproduzivel.
COPY --from=ghcr.io/astral-sh/uv:0.11.1 /uv /bin/uv

# Dependencias primeiro: aproveita o cache de camadas (o layer so e refeito
# quando pyproject.toml ou uv.lock mudam). --no-default-groups instala so
# [project.dependencies] (sem dev/pipeline) - inclui pandas e requests
# (necessarios por cadeia de imports em src.train -> src.prepare_dataset).
# --group api-onnx adiciona onnxruntime (Etapa 4/ADR-0011): so o runtime,
# nao skl2onnx/onnx -- backend fica opt-in via MODEL_BACKEND=onnx em
# runtime, sem custo se ninguem usar.
COPY pyproject.toml uv.lock ./
ENV UV_PROJECT_ENVIRONMENT=/usr/local
RUN uv sync --frozen --no-default-groups --group api-onnx --no-cache

# Codigo-fonte e artefato(s) do modelo (gerados por src/train.py /
# scripts/convert_to_onnx.py ou pela DAG). O bracket em "onn[x]" torna a
# copia do .onnx opcional: casa "model.onnx" se existir, nao casa nada
# (sem erro de build) se o arquivo nao tiver sido gerado localmente --
# COPY nao tem uma sintaxe "se existir" nativa, esse e o idiom usual.
COPY src/ ./src/
COPY models/model.pkl ./models/model.pkl
COPY models/model.onn[x] ./models/

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Health check em exec form: elimina dependencia de shell (sh/dash);
# /health responde 503 quando o modelo nao esta carregado, entao
# urlopen lanca HTTPError e o healthcheck falha corretamente.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]

CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
