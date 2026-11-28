"""交易维护单测：超时释放与状态对账（CAS 语义、幂等、不误伤已完成交易）。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import update

from app.common.enums import ItemStatus, TradeStatus
from app.modules.item.models import Item, TradeSession
from app.modules.item.service import expire_stale_trades, reconcile_trade_states

pytestmark = pytest.mark.asyncio


async def _make_item(session, owner_id: str, status: int = ItemStatus.RESERVED.value) -> Item:
    item = Item(
        owner_id=owner_id,
        title="维护测试",
        description="",
        price=100,
        category="other",
        status=status,
    )
    session.add(item)
    await session.flush()
    return item


async def _make_trade(
    session,
    item_id: str,
    buyer_id: str,
    seller_id: str,
    created_at: datetime,
    status: int = TradeStatus.PENDING.value,
) -> TradeSession:
    trade = TradeSession(
        item_id=item_id,
        buyer_id=buyer_id,
        seller_id=seller_id,
        status=status,
    )
    session.add(trade)
    await session.flush()
    # 绕过 server_default，直接设定 created_at 以模拟超时。
    await session.execute(
        update(TradeSession)
        .where(TradeSession.id == trade.id)
        .values(created_at=created_at)
    )
    return trade


async def test_expire_stale_trades_releases_reservation(session_factory):
    """超时的活跃会话被取消，物品回到 ON_SALE。"""
    async with session_factory() as s:
        item = await _make_item(s, "owner-1")
        trade = await _make_trade(
            s, str(item.id), "buyer-1", "owner-1", datetime.now(UTC) - timedelta(minutes=45)
        )
        trade_id = str(trade.id)
        item_id = str(item.id)
        await s.commit()

    async with session_factory() as s:
        result = await expire_stale_trades(s, timeout_minutes=30)
        assert result["expired"] == 1, result
        assert result["released"] == 1, result
        trade_after = await s.get(TradeSession, trade_id)
        item_after = await s.get(Item, item_id)
        assert trade_after.status == TradeStatus.CANCELLED.value
        assert item_after.status == ItemStatus.ON_SALE.value


async def test_expire_stale_trades_skips_fresh_and_completed(session_factory):
    """未超时会话与已完成会话不受影响。"""
    async with session_factory() as s:
        fresh_item = await _make_item(s, "owner-2")
        fresh_trade = await _make_trade(
            s, str(fresh_item.id), "buyer-2", "owner-2", datetime.now(UTC) - timedelta(minutes=5)
        )
        done_item = await _make_item(s, "owner-3", status=ItemStatus.SOLD.value)
        done_trade = await _make_trade(
            s, str(done_item.id), "buyer-3", "owner-3",
            datetime.now(UTC) - timedelta(minutes=90),
            status=TradeStatus.COMPLETED.value,
        )
        fresh_id, done_id = str(fresh_trade.id), str(done_trade.id)
        await s.commit()

    async with session_factory() as s:
        result = await expire_stale_trades(s, timeout_minutes=30)
        assert result["expired"] == 0, result
        assert (await s.get(TradeSession, fresh_id)).status == TradeStatus.PENDING.value
        assert (await s.get(TradeSession, done_id)).status == TradeStatus.COMPLETED.value


async def test_expire_stale_trades_disabled_when_zero(session_factory):
    """timeout_minutes=0 关闭自动释放。"""
    async with session_factory() as s:
        result = await expire_stale_trades(s, timeout_minutes=0)
        assert result["scanned"] == 0 and result["expired"] == 0


async def test_reconcile_releases_orphan_reserved_item(session_factory):
    """RESERVED 但无活跃会话的僵尸物品被释放回 ON_SALE。"""
    async with session_factory() as s:
        item = await _make_item(s, "owner-4")
        item_id = str(item.id)
        await s.commit()

    async with session_factory() as s:
        result = await reconcile_trade_states(s)
        assert result["orphans_released"] == 1, result
        assert (await s.get(Item, item_id)).status == ItemStatus.ON_SALE.value


async def test_reconcile_cancels_mismatched_active_session(session_factory):
    """活跃会话但物品已非 RESERVED → 会话被取消，释放唯一索引占用。"""
    async with session_factory() as s:
        item = await _make_item(s, "owner-5", status=ItemStatus.ON_SALE.value)
        trade = await _make_trade(
            s, str(item.id), "buyer-5", "owner-5", datetime.now(UTC),
        )
        trade_id = str(trade.id)
        await s.commit()

    async with session_factory() as s:
        result = await reconcile_trade_states(s)
        assert result["sessions_cancelled"] == 1, result
        assert (await s.get(TradeSession, trade_id)).status == TradeStatus.CANCELLED.value


async def test_reconcile_is_idempotent(session_factory):
    """对账重复执行无副作用。"""
    async with session_factory() as s:
        await _make_item(s, "owner-6")
        await s.commit()

    async with session_factory() as s:
        first = await reconcile_trade_states(s)
    async with session_factory() as s:
        second = await reconcile_trade_states(s)
    assert first["orphans_released"] == 1
    assert second["orphans_released"] == 0
