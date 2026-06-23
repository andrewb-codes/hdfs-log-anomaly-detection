FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src
ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-group notebooks

COPY src ./src
COPY configs ./configs
COPY alembic.ini .
COPY migrations ./migrations

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn hdfs_anomaly.api.app:app --host 0.0.0.0 --port 8000"]
