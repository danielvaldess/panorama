FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUTF8=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY pipeline/ ./pipeline/
COPY eval/ ./eval/
COPY web/ ./web/
COPY data/ ./data/

EXPOSE 80
CMD ["python", "-m", "uvicorn", "pipeline.server:app", "--host", "0.0.0.0", "--port", "80"]
