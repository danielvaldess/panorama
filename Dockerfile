FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUTF8=1 \
    PANORAMA_DB=/app/data/panorama.db

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Pre-descarga el modelo de embeddings para que la demo funcione sin internet
ENV FASTEMBED_CACHE=/app/.fastembed_cache
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2', cache_dir='/app/.fastembed_cache')"

COPY pipeline/ ./pipeline/
COPY eval/ ./eval/
COPY web/ ./web/
COPY data/ ./data/

# data/ contiene la DB operativa (panorama.db) y el caché del LLM: monta esta
# carpeta como volumen persistente en el despliegue (ver docs/DB.md).
VOLUME ["/app/data"]

EXPOSE 80
CMD ["python", "-m", "uvicorn", "pipeline.server:app", "--host", "0.0.0.0", "--port", "80"]
