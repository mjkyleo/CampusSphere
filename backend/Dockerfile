# 后端镜像（FastAPI 模块化单体）
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 系统依赖（用于编译 psycopg/uvicorn）
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install fastapi "uvicorn[standard]" sqlalchemy aiosqlite \
    pydantic pydantic-settings pyjwt "passlib[bcrypt]" bcrypt redis structlog httpx pyyaml \
    prometheus-client celery asyncpg minio meilisearch opentelemetry-api opentelemetry-sdk \
    opentelemetry-instrumentation-fastapi

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

EXPOSE 8000

# 开发/默认：SQLite 零依赖启动；生产请通过环境变量注入 DB_URL 等
CMD ["uvicorn", "app.asgi:app", "--host", "0.0.0.0", "--port", "8000"]
