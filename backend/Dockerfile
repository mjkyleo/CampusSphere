# 后端镜像（FastAPI 模块化单体）—— 多阶段构建 + 非 root + 健康检查
#
# 阶段划分：
#   builder : 安装编译依赖（gcc/libpq-dev），在隔离 venv 中按 pyproject 安装运行依赖与 app 包。
#   runtime : 仅携带 venv（已编译产物）+ alembic 配置，以非 root 用户运行，体积更小、攻击面更低。
#
# 版本锁定说明：当前依赖经 pyproject 的 >= 下限约束；生产建议后续生成锁定文件
# （如 uv.lock / pip-tools 的 requirements.txt --generate-hashes）并提交，以保证可复现构建。
# 基础镜像固定到 python:3.12-slim（小版本漂移可控）。

# ---------------- 构建阶段 ----------------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

# 编译期依赖（psycopg/asyncpg 需要 libpq-dev 与 gcc；仅存在于 builder，不带入运行镜像）
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制构建产物所需源码与依赖清单；pip install . 会按 [project].dependencies 安装并打包 app
COPY pyproject.toml ./
COPY app ./app

RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install .

# ---------------- 运行阶段 ----------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# 运行期仅需运行时库（psycopg 驱动等已在 venv 中），无需 gcc
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/* \
    # 创建非 root 用户运行服务，降低容器逃逸风险
    && useradd --create-home --uid 10001 appuser

WORKDIR /app

# 复用 builder 中已装好依赖的 venv（含已安装的 app 包）
COPY --from=builder /opt/venv /opt/venv
# alembic 迁移配置不在 app 包内，需单独带入
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

USER appuser

EXPOSE 8000

# 健康检查：根路径 / 返回 200 即视为存活（见 app/main.py root 路由）。
# 探测用 python 标准库，避免额外安装 curl 之外的探测工具。
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/').status==200 else 1)"

# 开发/默认：SQLite 零依赖启动；生产请通过环境变量注入 DB_URL、REDIS_URL 等
CMD ["uvicorn", "app.asgi:app", "--host", "0.0.0.0", "--port", "8000"]
