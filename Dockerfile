FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-api.txt .
RUN pip install --no-cache-dir --timeout 120 --retries 5 -r requirements-api.txt
RUN pip install --no-cache-dir --timeout 120 --retries 5 \
    --index-url https://download.pytorch.org/whl/cpu \
    torch==2.12.1

COPY src ./src
COPY configs ./configs
COPY alembic.ini .
COPY migrations ./migrations

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn hdfs_anomaly.api.app:app --host 0.0.0.0 --port 8000"]
