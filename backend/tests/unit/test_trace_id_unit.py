"""Task 6 单元测试：全链路 trace_id 染色（ContextVar → SQL 注释）。

覆盖点：
1. trace id 通过 ContextVar 在请求上下文内传递。
2. SQL 语句被注入 ``/* trace_id=xxx */`` 注释；无 trace id 时不加注释。
3. **安全**：X-Request-ID 来自客户端请求头，必须消毒后再拼进 SQL 注释，
   否则 ``*/ DROP TABLE users; --`` 能闭合注释块实施注入。
4. 真实执行 SQL 时注释确实生效（do_execute 接管执行路径的端到端验证）。

为什么用 ``do_execute`` 接管，而不用 ``before_cursor_execute`` 的返回值改写：
在 SQLAlchemy 2.0.30 中，``before_cursor_execute`` 的返回值被**忽略**——
监听器确实被调用、也返回了改写后的语句，但数据库执行的仍是原语句
（Core select 与 text() 两条路径、Engine/Connection 实例级与类级四种注册方式
均如此，已实测）。因此生产代码改为由 ``do_execute`` / ``do_execute_no_params``
监听器自己执行改写后的语句并返回 True（告知 SQLAlchemy "已处理"）。
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.core.database import (
    _commented,
    _do_execute_no_params_with_trace,
    _do_execute_with_trace,
)
from app.core.logging import (
    bind_request,
    clear_request,
    get_trace_id,
    sanitize_trace_id,
)


@pytest.fixture(autouse=True)
def _clean_trace():
    """每个用例前后清空 trace 上下文，避免用例间串味。"""
    clear_request()
    yield
    clear_request()


# ---------------------------------------------------------------------------
# trace id 消毒（安全底线）
# ---------------------------------------------------------------------------
def test_sanitize_keeps_normal_ids() -> None:
    assert sanitize_trace_id("abc123") == "abc123"
    assert sanitize_trace_id("req-1_2.3") == "req-1_2.3"


def test_sanitize_strips_sql_comment_breakout() -> None:
    """攻击者用 */ 提前闭合注释 —— 必须被剥离。

    安全字符集是 ``[A-Za-z0-9_.:-]``，所以空格、星号、斜杠、分号、连字空格
    全部被删除，只留下连续的合法字符。
    """
    cleaned = sanitize_trace_id("x */ DROP TABLE users; --")
    # 非法字符（空格、*、/、;）被删除后，剩下 "xDROPTABLEusers--"
    # （末尾两个连字符 "-" 属于合法字符集，会被保留）
    assert cleaned == "xDROPTABLEusers--"
    assert "*/" not in cleaned
    assert "DROP TABLE" not in cleaned  # 已被拆散，无法再构成危险语句
    assert "*/" not in sanitize_trace_id("a*/b")


def test_sanitize_strips_quotes_and_spaces() -> None:
    assert sanitize_trace_id("a'b\"c d") == "abcd"


def test_sanitize_caps_length() -> None:
    assert len(sanitize_trace_id("a" * 500)) == 64


def test_sanitize_handles_empty() -> None:
    assert sanitize_trace_id(None) is None
    assert sanitize_trace_id("") is None
    assert sanitize_trace_id("***") is None


# ---------------------------------------------------------------------------
# ContextVar 传递
# ---------------------------------------------------------------------------
def test_bind_request_sets_trace_id() -> None:
    bind_request("req-xyz")
    assert get_trace_id() == "req-xyz"


def test_clear_request_unsets_trace_id() -> None:
    bind_request("req-xyz")
    clear_request()
    assert get_trace_id() is None


# ---------------------------------------------------------------------------
# _commented：statement -> 注释包裹
# ---------------------------------------------------------------------------
def test_commented_injects_trace_id() -> None:
    bind_request("abc123")
    assert _commented("SELECT 1") == "/* trace_id=abc123 */ SELECT 1"


def test_commented_returns_none_without_trace() -> None:
    """后台任务 / lifespan 没有请求上下文：不加无意义的空注释。"""
    assert _commented("SELECT 1") is None


def test_commented_sanitizes_malicious_id() -> None:
    """消毒后的恶意 id 无法闭合注释块：语句里仍只有一对注释定界符。"""
    bind_request("x */ DELETE FROM users; --")
    commented = _commented("SELECT 1")
    assert commented is not None
    # 闭合符 "*/" 已被剥离，整条语句仅由我们控制的一对 /* */ 包裹
    assert commented.count("/*") == 1
    assert commented.count("*/") == 1
    # 危险内容仍在注释内部（被定界符夹住），不会逃逸到注释外执行
    assert "*/" not in commented.split("/*", 1)[1].split("*/", 1)[0]


# ---------------------------------------------------------------------------
# do_execute 接管 handler：直接调用，断言它把注释后的语句交给 cursor 执行
# ---------------------------------------------------------------------------
def test_do_execute_handler_injects_and_takes_over() -> None:
    """handler 必须把注释后的语句交给 cursor.execute 并返回 True（接管执行）。"""
    bind_request("abc123")
    cursor = MagicMock()
    result = _do_execute_with_trace(cursor, "SELECT 1", (1,), context=None)
    cursor.execute.assert_called_once_with(
        "/* trace_id=abc123 */ SELECT 1", (1,)
    )
    assert result is True


def test_do_execute_handler_yields_when_no_trace() -> None:
    """无请求上下文：不执行、返回 False（交回默认执行路径）。"""
    cursor = MagicMock()
    result = _do_execute_with_trace(cursor, "SELECT 1", (), context=None)
    cursor.execute.assert_not_called()
    assert result is False


def test_do_execute_no_params_handler() -> None:
    """无参 SQL（如 DDL）同样注入注释并接管。"""
    bind_request("abc123")
    cursor = MagicMock()
    result = _do_execute_no_params_with_trace(cursor, "SELECT 1", context=None)
    cursor.execute.assert_called_once_with("/* trace_id=abc123 */ SELECT 1")
    assert result is True


# ---------------------------------------------------------------------------
# 端到端：真实引擎上 do_execute 接管确实改变了「实际执行」的语句
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_do_execute_takeover_changes_executed_sql() -> None:
    """回归测试：do_execute 接管机制确实改变数据库**实际执行**的语句。

    这正是 Task 6 的关键发现 —— before_cursor_execute 的返回值在 2.0.30
    不生效，必须用 do_execute 接管。本用例用 ``SELECT 42`` -> ``SELECT 99``
    证明：监听器改写后的语句才是真正被执行的。
    """
    from sqlalchemy import event, text
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine("sqlite+aiosqlite://", future=True)

    def _rewrite(cursor, statement, parameters, context):
        if statement.strip() == "SELECT 42":
            cursor.execute("SELECT 99", parameters)
            return True
        return False

    event.listen(engine.sync_engine, "do_execute", _rewrite)
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 42"))
        value = result.scalar()
    assert value == 99

    await engine.dispose()
