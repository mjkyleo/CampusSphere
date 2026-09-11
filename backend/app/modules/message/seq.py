"""会话消息序号（LocalSeq）—— 断线重连的精准补发基线。

为什么时间戳（``since``）不够用
------------------------------
原实现按 ``created_at > since`` 拉取增量。时间戳精度有限（数据库通常到秒或
毫秒），同一时间刻度内的多条消息无法区分，于是产生两类错误：

* **丢消息**：用最后一条的时间戳做游标，与之**同刻度**的其它消息被
  ``>`` 排除，永久丢失；
* **重复推**：为保险把条件放宽成 ``>=``，最后一条又被重复推送一遍。

单调递增的**序号**没有这个问题：游标语义精确（"我收到第 N 条了"），
补发区间是 ``(N, +inf]``，不重不漏。

为什么用 Redis ZSet
-------------------
补发需要"按区间取有序元素"，ZSet 天然满足：member 存消息体，score 存 seq，
``ZRANGEBYSCORE (N +inf`` 一次拿回全部缺失消息。它同时自带：

* **多实例一致**：序号由 Redis 的 ``INCR`` 分配，各实例不会撞号；
* **自动老化**：``ZREMRANGEBYRANK`` 裁剪尾部，避免无限增长。

降级策略
--------
Redis 不可用时退化为**进程内**序号表（单实例语义正确，多实例会各发各的号）。
这与 ``app.core.redis`` 整体的"降级不中断"策略一致：功能退化，但连接不断。
"""

from __future__ import annotations

import asyncio
import json

from app.core.logging import get_logger
from app.core.redis import get_redis

_logger = get_logger("message.seq")

# 每个会话保留的最大序号条目数：补发只需覆盖"短暂断线"窗口，
# 长时间离线应由客户端走历史消息接口，而不是让 ZSet 无限膨胀。
DEFAULT_MAX_ENTRIES = 500


class LocalSeqStore:
    """会话级单调递增序号存储（Redis ZSet，无 Redis 时内存降级）。"""

    def __init__(self, prefix: str = "ws:seq:", max_entries: int = DEFAULT_MAX_ENTRIES) -> None:
        self._prefix = prefix
        self._max_entries = max_entries
        # 内存降级：conversation_id -> [(seq, payload_json), ...]（按 seq 升序）
        self._memory: dict[str, list[tuple[int, str]]] = {}
        self._lock = asyncio.Lock()

    def _key(self, conversation_id: str) -> str:
        return f"{self._prefix}{conversation_id}"

    async def append(self, conversation_id: str, payload: dict) -> int:
        """为一条消息分配序号并写入补发缓冲区，返回其 ``seq``。

        序号由 Redis ``INCR`` 分配（原子、跨实例唯一），随后以该值作为
        score 写入 ZSet —— 两步之间无需事务：即使 ZADD 失败，也只是
        该条消息不参与补发，序号出现空洞并不会破坏游标语义
        （补发取的是区间，不是连续序列）。
        """
        data = json.dumps(payload, default=str)
        client = await get_redis()
        key = self._key(conversation_id)

        if client is not None:
            try:
                seq = int(await client.incr(f"{key}:ctr"))
                await client.zadd(key, {data: seq})
                # 只保留最近 max_entries 条，裁剪最旧的若干条
                await client.zremrangebyrank(key, 0, -(self._max_entries + 1))
                return seq
            except Exception as exc:
                _logger.warning("seq_append_failed_fallback_memory", error=str(exc))

        async with self._lock:
            rows = self._memory.setdefault(conversation_id, [])
            seq = (rows[-1][0] + 1) if rows else 1
            rows.append((seq, data))
            if len(rows) > self._max_entries:
                del rows[:-self._max_entries]
            return seq

    async def since(
        self, conversation_id: str, last_seq: int = 0, limit: int = 200
    ) -> list[tuple[int, dict]]:
        """返回 ``seq > last_seq`` 的消息（按 seq 升序），供断线补发。

        :param last_seq: 客户端已确认收到的最后序号；``0`` 表示全量补发。
        :return: ``[(seq, payload), ...]``
        """
        client = await get_redis()
        key = self._key(conversation_id)
        # 开区间 ``(last_seq`` 是精确补发的关键：不含客户端已收到的那一条
        min_score = f"({last_seq}" if last_seq > 0 else "-inf"

        if client is not None:
            try:
                rows = await client.zrangebyscore(
                    key, min_score, "+inf", start=0, num=limit, withscores=True
                )
                out: list[tuple[int, dict]] = []
                for member, score in rows:
                    try:
                        out.append((int(score), json.loads(member)))
                    except (json.JSONDecodeError, ValueError):
                        continue
                return out
            except Exception as exc:
                _logger.warning("seq_since_failed_fallback_memory", error=str(exc))

        async with self._lock:
            rows_mem = self._memory.get(conversation_id, [])
            result: list[tuple[int, dict]] = []
            for seq, data in rows_mem:
                if seq <= last_seq:
                    continue
                try:
                    result.append((seq, json.loads(data)))
                except json.JSONDecodeError:
                    continue
                if len(result) >= limit:
                    break
            return result

    def clear_memory(self) -> None:
        """清空内存降级缓冲（供测试隔离使用）。"""
        self._memory.clear()


# 模块级单例：与 ws.manager 一样，进程内共享一份序号表
seq_store = LocalSeqStore()
