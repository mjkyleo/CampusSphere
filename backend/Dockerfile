# 后端镜像（FastAPI 模块化单体）—— 多阶段构建 + 非 root + 健康检查
#
# 本文件用 **单一 Dockerfile 承载两个 target**，供 docker compose 分别构建：
#   docker build --target app    -t campusphere-backend:latest .   # API 服务
#   docker build --target worker -t campusphere-worker:latest .    # Celery worker
#
# 为何不用两个 Dockerfile：两者 95% 的内容（编译依赖、venv、alembic、非 root 用户
# 与目录权限）完全相同。拆成两份必然产生漂移——改了一处忘了另一处，
# 就会出现"worker 缺某个依赖"这类只在生产暴露的问题。
#
# 阶段划分：
#   builder : 安装编译依赖（gcc/libpq-dev），在隔离 venv 中按 pyproject 安装运行依赖与 app 包。
#   base    : 仅携带 venv（已编译产物）+ alembic 配置，以非 root 用户运行 —— app 与 worker 共用。
#   app     : CMD = uvicorn；   worker : CMD = celery。
#
# 版本锁定说明：当前依赖经 pyproject 的 >= 下限约束；生产建议后续生成锁定文件
# （如 uv.lock / pip-tools 的 requirements.txt --generate-hashes）并提交，以保证可复现构建。
# 基础镜像固定到 python:3.12-slim（小版本漂移可控）。

# ---------------- 构建阶段 ----------------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# ---- 镜像源（构建期可覆盖）----
#
# 为何用 ARG 而非写死：docker build 在**容器内部**联网，Docker Desktop 配置的
# 代理对容器内 apt/pip 不生效；但若把国内源写死，海外 CI（GitHub Actions）反而会更慢。
# 故默认保持官方源确保可移植，国内构建时通过 --build-arg 或 compose 注入镜像。
#
# 实测（国内网络）：apt 官方源约 60 kB/s，装完 gcc 依赖需 30 分钟以上；
# 换阿里云镜像后约数 MB/s，同一步骤降到 1～2 分钟。这是构建耗时的**主要瓶颈**。
ARG APT_MIRROR=""
ARG PIP_INDEX_URL=""

WORKDIR /build

# 编译期依赖（psycopg/asyncpg 需要 libpq-dev 与 gcc；仅存在于 builder，不带入运行镜像）
# 若指定了 apt 镜像则替换默认源。Debian 13(trixie) 使用 DEB822 格式，
# 配置文件在 sources.list.d/debian.sources（旧版是 /etc/apt/sources.list）。
RUN if [ -n "$APT_MIRROR" ]; then \
        sed -i "s|deb.debian.org|${APT_MIRROR}|g" /etc/apt/sources.list.d/debian.sources 2>/dev/null \
        || sed -i "s|deb.debian.org|${APT_MIRROR}|g" /etc/apt/sources.list; \
    fi \
    && apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制构建产物所需源码与依赖清单；pip install . 会按 [project].dependencies 安装并打包 app
COPY pyproject.toml ./
COPY app ./app

# 复用上面的 PIP_INDEX_URL（为空则回退 pip 默认源）。
# 用 ${VAR:+...} 形式：未指定时不设置该环境变量，避免留下空值影响 pip 行为。
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && PIP_INDEX_URL="${PIP_INDEX_URL}" /opt/venv/bin/pip install . \
    # 构建期冒烟：直接导入应用，确保依赖**完整**。
    # 必要性：曾有 email-validator 未声明进 pyproject，而它在开发机上恰好已存在，
    # 导致本地测试全绿、容器里 `from app.main import app` 直接 ModuleNotFoundError。
    # 兜在构建期，避免"镜像构建成功但一启动就崩"。
    && /opt/venv/bin/python -c "from app.main import app; print('build smoke: app import OK')"

# ---------------- 运行基础阶段（app / worker 共用）----------------
FROM python:3.12-slim AS base

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

# ---------------- API 服务 ----------------
FROM base AS app

EXPOSE 8000

# 健康检查：根路径 / 返回 200 即视为存活（见 app/main.py root 路由）。
# 探测用 python 标准库，避免额外安装 curl 之外的探测工具。
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/').status==200 else 1)"

# 开发/默认：SQLite 零依赖启动；生产请通过环境变量注入 DB_URL、REDIS_URL 等
CMD ["uvicorn", "app.asgi:app", "--host", "0.0.0.0", "--port", "8000"]

# ---------------- Celery Worker ----------------
FROM base AS worker

# Worker 健康检查：向 Broker 探活自身（依赖 Redis 可达；不可达即判定不健康）。
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD celery -A app.tasks.celery_app.celery_app inspect ping || exit 1

# 启动 Celery Worker（邮件/通知/搜索同步队列）
CMD ["celery", "-A", "app.tasks.celery_app.celery_app", "worker", "--loglevel=info", "-Q", "email,notify,search,default"]
