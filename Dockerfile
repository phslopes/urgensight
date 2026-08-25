# Dockerfile da API de inferencia (Etapa 2) -- UrgenSight.
# Nao confundir com Dockerfile.airflow (orquestracao Airflow, Etapa 1.3).
#
# Build:  docker build -t urgensight-api .
# Run:    docker run -d -p 8000:8000 --name urgensight-api urgensight-api
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Usuario nao-root para execucao da API.
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

WORKDIR /app

# Dependencias primeiro: aproveita o cache de camadas do Docker (o layer de
# dependencias so e refeito quando requirements.txt muda).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Codigo-fonte e artefato do modelo (gerado por src/train.py ou pela DAG).
COPY src/ ./src/
COPY models/model.pkl ./models/model.pkl

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Health check em exec form: elimina dependencia de shell (sh/dash);
# /health responde 503 quando o modelo nao esta carregado, entao
# urlopen lanca HTTPError e o healthcheck falha corretamente.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]

CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
