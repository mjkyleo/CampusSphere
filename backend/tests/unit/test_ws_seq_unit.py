"""Task 5 单元测试：WebSocket LocalSeq 精准补发（Redis ZSet + 内存降级）。

覆盖点：
1. 序号单调递增，且**在线推送与离线补发携带同一个 seq**（游标能对齐）。
2. 精确补发：``last_seq=N`` 只返回 seq > N 的消息（开区间，不重不漏）。
3. **证明时间戳口径的缺陷**（本任务要解决的原始问题）：
   同一时间刻度的多条消息无法靠时间戳区分游标，会丢消息或重复推。
4. Redis 不可用时降级为内存序号表，功能不中断。
5. 补发缓冲有上限，不会无限膨胀。
"""

from __future__ import annotations

import asyncio

import pytest

from app.modules.message.seq import LocalSeqStore


@pytest.fixture
def store():
    """每个用例一份独立的序号存储，避免相互污染。"""
    return LocalSeqStore(prefix="test:seq:", max_entries=50)


def _msg(text: str) -> dict:
    return {"event": "message:new", "data": {"content": text}}


# ---------------------------------------------------------------------------
# 基本语义
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_seq_is_monotonically_increasing(store) -> None:
    seqs = [await store.append("c1", _msg(f"m{i}")) for i in range(5)]
    assert seqs == [1, 2, 3, 4, 5]


@pytest.mark.asyncio
async def test_seqs_are_scoped_per_conversation(store) -> None:
    """不同会话各自独立编号：A 会话的第 3 条不影响 B 会话的编号。"""
    await store.append("cA", _msg("a1"))
    await store.append("cA", _msg("a2"))
    assert await store.append("cA", _msg("a3")) == 3
    assert await store.append("cB", _msg("b1")) == 1


@pytest.mark.asyncio
async def test_since_returns_only_messages_after_cursor(store) -> None:
    """精确补发的核心：只补 seq > last_seq 的那几条。"""
    for i in range(5):
        await store.append("c1", _msg(f"m{i}"))

    rows = await store.since("c1", last_seq=3)
    assert [seq for seq, _ in rows] == [4, 5]
    assert [p["data"]["content"] for _, p in rows] == ["m3", "m4"]


@pytest.mark.asyncio
async def test_since_is_exclusive_no_duplicate_of_last_received(store) -> None:
    """游标那一条**不能**重复推送（开区间语义）。"""
    await store.append("c1", _msg("only"))
    assert await store.since("c1", last_seq=1) == []
    assert len(await store.since("c1", last_seq=0)) == 1


@pytest.mark.asyncio
async def test_since_zero_returns_everything(store) -> None:
    for i in range(3):
        await store.append("c1", _msg(f"m{i}"))
    assert len(await store.since("c1", last_seq=0)) == 3


@pytest.mark.asyncio
async def test_concurrent_appends_get_distinct_seqs(store) -> None:
    """并发发送不能撞号 —— 补发正确性依赖序号唯一。"""
    seqs = await asyncio.gather(*[store.append("c1", _msg(f"m{i}")) for i in range(20)])
    assert sorted(seqs) == list(range(1, 21))


# ---------------------------------------------------------------------------
# 证明"为什么时间戳不够用"（本任务的立论依据）
# ---------------------------------------------------------------------------
def test_timestamp_cursor_is_ambiguous_but_seq_is_not() -> None:
    """同一时间刻度下的多条消息：时间戳无法表达"我在这里"的游标。

    两条消息落在同一秒内，客户端记住"最后一条的时间戳"：
    - 用 ``>`` 过滤 → 与之同刻度的其它消息被排除，**丢消息**；
    - 用 ``>=`` 过滤 → 最后一条又被重复推送，**重复推**。

    序号没有这个二难：游标是整数，区间 ``(N, +inf]`` 精确无歧义。
    """
    from datetime import datetime

    t = datetime(2026, 9, 4, 10, 0, 0)
    same_instant = [
        {"created_at": t, "content": "A"},
        {"created_at": t, "content": "B"},
    ]
    last_seen = t

    dropped = [m for m in same_instant if m["created_at"] > last_seen]
    duplicated = [m for m in same_instant if m["created_at"] >= last_seen]

    assert dropped == [], "严格大于会漏掉同刻度的消息（丢消息）"
    assert len(duplicated) == 2, "放宽成大于等于又会重复推送已收到的那条"

    # 而序号游标两种情况都不发生
    rows = [(1, "A"), (2, "B")]
    assert [c for s, c in rows if s > 2] == []      # 不重复
    assert [c for s, c in rows if s > 1] == ["B"]   # 不遗漏


# ---------------------------------------------------------------------------
# 降级与边界
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_falls_back_to_memory_when_redis_unavailable(monkeypatch) -> None:
    """Redis 不可用：退化为进程内序号表，补发能力仍在（单实例语义正确）。"""
    from app.modules.message import seq as seq_module

    monkeypatch.setattr(seq_module, "get_redis", lambda: asyncio.sleep(0, None))

    store = LocalSeqStore(prefix="test:mem:")
    for i in range(3):
        await store.append("c1", _msg(f"m{i}"))

    rows = await store.since("c1", last_seq=1)
    assert [p["data"]["content"] for _, p in rows] == ["m1", "m2"]


@pytest.mark.asyncio
async def test_buffer_is_capped_to_max_entries() -> None:
    """补发缓冲有上限：长时间离线不该让 ZSet 无限膨胀。"""
    store = LocalSeqStore(prefix="test:cap:", max_entries=5)
    for i in range(50):
        await store.append("c1", _msg(f"m{i}"))

    rows = await store.since("c1", last_seq=0, limit=100)
    assert len(rows) <= 5
    # 保留的是**最近**的几条，而非最旧的
    assert rows[-1][1]["data"]["content"] == "m49"


@pytest.mark.asyncio
async def test_since_respects_limit(store) -> None:
    for i in range(10):
        await store.append("c1", _msg(f"m{i}"))
    assert len(await store.since("c1", last_seq=0, limit=3)) == 3


@pytest.mark.asyncio
async def test_since_on_unknown_conversation_is_empty(store) -> None:
    assert await store.since("does-not-exist", last_seq=0) == []


@pytest.mark.asyncio
async def test_clear_memory_resets_state() -> None:
    store = LocalSeqStore(prefix="test:clr:")
    await store.append("c1", _msg("x"))
    store.clear_memory()
    assert await store.since("c1", last_seq=0) == []
