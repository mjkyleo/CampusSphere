"""pytest 公共夹具：隔离测试库、覆盖 DB 依赖。

设计要点：
- 使用独立的临时 SQLite 文件作为测试库，避免污染开发库 dev.db。
- 通过 ``app.dependency_overrides`` 将 ``get_db`` 指向测试库会话。
- Redis / MinIO / Meilisearch 均走代码内建的降级逻辑（内存兜底 / 本地磁盘 / 空结果），
  因此测试无需任何外部中间件即可在零依赖环境下跑通。
- 认证助手见 ``tests/helpers.py``。
"""

from __future__ import annotations

import os
import sys
import tempfile
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# 单测环境关闭热点缓存：避免内存降级字典在用例间残留造成列表查询命中旧数据。
# 缓存逻辑本身由后端单元/集成测试单独覆盖，这里只保证业务用例互不影响。
os.environ.setdefault("CACHE_ENABLED", "false")

# 将 backend/ 与 backend/tests/ 加入 sys.path，确保 ``import app`` 与 ``import helpers`` 可用
_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)
_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)

from app.common.models import Base  # noqa: E402
from app.core.database import get_db  # noqa: E402

# 导入所有业务模型，确保表结构注册到 Base.metadata
import app.modules.admin.models  # noqa: E402,F401
import app.modules.auth.models  # noqa: E402,F401
import app.modules.canteen.models  # noqa: E402,F401
import app.modules.course.models  # noqa: E402,F401
import app.modules.item.models  # noqa: E402,F401
import app.modules.job.models  # noqa: E402,F401
import app.modules.message.models  # noqa: E402,F401
import app.modules.report.models  # noqa: E402,F401
import app.modules.share.models  # noqa: E402,F401
import app.modules.teammate.models  # noqa: E402,F401
import app.modules.user.models  # noqa: E402,F401

from app.core.config import settings  # noqa: E402
from app.main import app  # noqa: E402

_TEST_DB = os.path.join(tempfile.gettempdir(), "campus_test.db")


@pytest.fixture(autouse=True)
def _disable_redis_connection(monkeypatch):
    """测试环境禁用真实 Redis 连接，强制走内存降级，避免每次请求 0.5s 连接超时。

    Redis 降级逻辑已在生产代码中实现（connect 失败回退内存），此处只是让失败即时发生。
    """
    import redis.asyncio as _aioredis

    def _boom(*_args, **_kwargs):
        raise ConnectionError("redis disabled in tests")

    monkeypatch.setattr(_aioredis, "from_url", _boom)


@pytest.fixture(autouse=True)
def _relax_rate_limit():
    """放宽测试环境限流阈值。

    限流按客户端 IP + 分钟窗口计数（Redis 禁用时走内存兜底），
    完整测试套件在同一分钟窗口内会累计大量请求，默认 120 会误触发 429。
    中间件栈在每次请求时基于 user_middleware 构建，此处修改 options 即可生效。
    """
    from app.core.middleware import GatewayMiddleware

    for mw in app.user_middleware:
        if mw.cls is GatewayMiddleware:
            mw.kwargs["rate_limit_per_minute"] = 100_000


@pytest.fixture(autouse=True)
def _relax_admin_gateway():
    """测试环境放宽管理端网关校验：既有测试直接调用 /api/admin/* 不携带网关令牌。

    网关强制校验是生产默认行为，由 AdminGateway 相关测试显式开启验证；
    此处默认关闭，保证既有管理后台测试无需改动即可通过。
    """
    settings.admin_gateway_enforce = False
    yield
    settings.admin_gateway_enforce = True


@pytest.fixture(scope="function")
async def test_engine():
    engine = create_async_engine(f"sqlite+aiosqlite:///{_TEST_DB}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()
    if os.path.isfile(_TEST_DB):
        try:
            os.remove(_TEST_DB)
        except OSError:
            pass


@pytest_asyncio.fixture
async def session_factory(test_engine):
    return async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
def sync_session_factory(test_engine):
    """基于同一测试库文件的同步 sessionmaker（供 Celery 同步任务测试）。"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker as sync_sessionmaker

    db_file = test_engine.url.database
    sync_engine = create_engine(f"sqlite:///{db_file}")
    return sync_sessionmaker(bind=sync_engine, expire_on_commit=False)


@pytest.fixture
def client(test_engine, session_factory):
    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    # 不使用 lifespan（避免创建 dev.db / 启动后台监听），依赖已在 fixture 中建好
    c = TestClient(app)
    yield c
    app.dependency_overrides.clear()


@pytest.fixture
def ws_client(client, session_factory, monkeypatch):
    """WebSocket 测试客户端：额外把 ``app.modules.message.ws`` 内的
    ``SessionLocal`` 指向测试库，否则 WS 消息发送会落到 dev.db。"""
    import app.modules.message.ws as ws_module

    monkeypatch.setattr(ws_module, "SessionLocal", session_factory)
    return client
