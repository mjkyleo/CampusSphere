"""OAuth 绑定唯一约束：DB 层最后一道防线。"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.modules.auth.models import OAuthAccount, User

pytestmark = pytest.mark.asyncio


async def test_oauth_account_unique_constraint_rejects_duplicate(session_factory):
    """同一 provider 的 openid 不能被插入两次（DB 最后一道防线）。

    service 层的 SELECT 预检无法防并发，唯一约束是真正的兜底；
    这里直接绕过 service 验证约束存在，避免测试依赖外部 OAuth 配置。
    """
    suffix = uuid.uuid4().hex[:8]
    async with session_factory() as s:
        u1 = User(username=f"oauth_a_{suffix}", password_hash="x")
        u2 = User(username=f"oauth_b_{suffix}", password_hash="x")
        s.add_all([u1, u2])
        await s.flush()
        s.add(OAuthAccount(user_id=u1.id, provider="wechat", provider_openid=f"openid-{suffix}"))
        await s.commit()

    async with session_factory() as s:
        u2 = (await s.scalars(
            select(User).where(User.username == f"oauth_b_{suffix}")
        )).one()
        s.add(OAuthAccount(user_id=u2.id, provider="wechat", provider_openid=f"openid-{suffix}"))
        with pytest.raises(IntegrityError):
            await s.commit()
        await s.rollback()


async def test_same_openid_different_provider_allowed(session_factory):
    """唯一约束是 (provider, openid) 组合，不同 provider 的同名 openid 可共存。"""
    suffix = uuid.uuid4().hex[:8]
    async with session_factory() as s:
        u = User(username=f"oauth_c_{suffix}", password_hash="x")
        s.add(u)
        await s.flush()
        s.add_all([
            OAuthAccount(user_id=u.id, provider="wechat", provider_openid=f"shared-{suffix}"),
            OAuthAccount(user_id=u.id, provider="qq", provider_openid=f"shared-{suffix}"),
        ])
        await s.commit()

    async with session_factory() as s:
        rows = (await s.scalars(
            select(OAuthAccount).where(OAuthAccount.provider_openid == f"shared-{suffix}")
        )).all()
        assert {r.provider for r in rows} == {"wechat", "qq"}
