FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.5.31 /uv /uvx /bin/

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-group notebooks --no-install-project

COPY src ./src
COPY configs ./configs
COPY alembic.ini .
COPY migrations ./migrations

RUN uv sync --frozen --no-dev --no-group notebooks

EXPOSE 8000 8501

CMD ["sh", "-c", "alembic upgrade head && uvicorn hdfs_anomaly.api.app:app --host 0.0.0.0 --port 8000"]
