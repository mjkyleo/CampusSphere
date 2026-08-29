"""集成测试层公共夹具。

集成测试的定义：**真实 HTTP 请求 + 真实数据库 + 外部服务走 mock/降级**。
本层提供两样东西：

1. ``db_session`` —— 与 ``client`` 共用同一个 ``test_engine`` 的异步会话，
   用于播种数据与断言落库结果（二者共享同一测试库文件，所以数据互通）；
2. ``fx`` —— 绑定该会话的 factory_boy 工厂入口，默认 **自动 commit**，
   保证播种的数据能被随后的 HTTP 请求看到。

数据隔离策略
------------
``tests/conftest.py`` 的 ``test_engine`` 是 **function 级**且每次
``drop_all + create_all``，因此每个用例都跑在一张干净的库上，
无需手动回滚，也不会出现用例间数据串扰。
"""

from __future__ import annotations

import pytest

from factories import create_async, create_batch_async


def pytest_collection_modifyitems(items):
    """自动为本目录下所有用例打 ``integration`` 标记。

    放在 conftest 的 ``pytestmark`` 只会作用于 conftest 自身，对子目录无效；
    用 collection 钩子才能真正实现"按目录分层"，后续新增文件无需手动加装饰器。
    """
    for item in items:
        item.add_marker(pytest.mark.integration)


class FactoryHub:
    """把 factory_boy 工厂绑定到当前测试的异步会话。

    用法::

        user = await fx.create(UserFactory, username="alice")
        items = await fx.batch(ItemFactory, 3, owner_id=user.id)
    """

    def __init__(self, session) -> None:
        self._session = session

    @property
    def session(self):
        """暴露底层会话，便于断言落库结果。"""
        return self._session

    async def create(self, factory_class, **kwargs):
        """创建并**提交**一个实例（默认 commit，确保 API 可见）。"""
        kwargs.setdefault("commit", True)
        return await create_async(self._session, factory_class, **kwargs)

    async def batch(self, factory_class, size: int, **kwargs):
        """批量创建并提交。"""
        kwargs.setdefault("commit", True)
        return await create_batch_async(self._session, factory_class, size, **kwargs)


@pytest.fixture(autouse=True)
def clean_memory_redis():
    """每个用例前后清空 Redis 内存兜底字典。

    内存降级**不支持 TTL**，验证码（``vcode:*``）、发送频率计数
    （``ratelimit:*``）、验证码尝试次数与 JWT 黑名单都会无限期残留。
    若不清空，"发送过于频繁"这类限流断言会被上一个用例的计数污染。
    """
    import app.core.redis as redis_module

    redis_module._memory_fallback.clear()
    yield
    redis_module._memory_fallback.clear()


@pytest.fixture
async def db_session(session_factory):
    """与 API client 共享同一测试库的异步会话。"""
    async with session_factory() as session:
        yield session


@pytest.fixture
def fx(db_session):
    """factory_boy 工厂入口（已绑定当前用例的会话）。"""
    return FactoryHub(db_session)
