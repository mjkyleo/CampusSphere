"""第三方 OAuth：微信 code2session、QQ OAuth2、state 防 CSRF、按 openid 绑定用户签发 JWT。"""

from __future__ import annotations

import uuid
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import UserStatus
from app.core.config import settings
from app.core.exceptions import BizError, ErrorCode
from app.core.logging import get_logger
from app.core.redis import redis_delete, redis_get, redis_set
from app.modules.auth.models import OAuthAccount, User

_logger = get_logger("auth.oauth")

_STATE_PREFIX = "oauth:state:"


async def generate_oauth_state(provider: str) -> str:
    """生成并存储 OAuth state（防 CSRF），TTL 来自 school.yaml。"""
    import secrets

    state = secrets.token_urlsafe(16)
    ttl = int((settings.oauth or {}).get("state_ttl", 300))
    await redis_set(f"{_STATE_PREFIX}{provider}:{state}", "1", ttl=ttl)
    return state


async def verify_oauth_state(provider: str, state: Optional[str]) -> bool:
    if not state:
        return False
    key = f"{_STATE_PREFIX}{provider}:{state}"
    ok = await redis_get(key) is not None
    if ok:
        await redis_delete(key)
    return ok


async def _get_or_create_user_by_openid(
    db: AsyncSession, provider: str, openid: str, nickname: str = ""
) -> tuple[User, bool]:
    """按 openid 查/建 OAuthAccount 与 User，返回 (user, is_new)。"""
    acct = await db.scalar(
        select(OAuthAccount).where(
            OAuthAccount.provider == provider,
            OAuthAccount.provider_openid == openid,
        )
    )
    if acct:
        user = await db.get(User, acct.user_id)
        return user, False
    # 新建用户 + 绑定
    username = f"{provider}_{openid[-12:]}"
    user = User(username=username, nickname=nickname, status=UserStatus.NORMAL.value)
    user.set_password(uuid.uuid4().hex)
    db.add(user)
    await db.flush()
    db.add(OAuthAccount(user_id=user.id, provider=provider, provider_openid=openid))
    await db.commit()
    await db.refresh(user)
    _logger.info("oauth_user_created", provider=provider, user_id=str(user.id))
    return user, True


async def _exchange_wechat_openid(code: str) -> str:
    """微信小程序 code2session，返回 openid。"""
    cfg = (settings.oauth or {}).get("wechat", {})
    appid = cfg.get("appid")
    secret = cfg.get("secret")
    if not appid or not secret:
        raise BizError(ErrorCode.INTERNAL, "微信 OAuth 未配置")
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            "https://api.weixin.qq.com/sns/jscode2session",
            params={
                "appid": appid,
                "secret": secret,
                "js_code": code,
                "grant_type": "authorization_code",
            },
        )
        data = resp.json()
    if "openid" not in data:
        _logger.error("wechat_code2session_failed", resp=data)
        raise BizError(ErrorCode.UNAUTHORIZED, "微信登录失败")
    return data["openid"]


async def _exchange_qq_openid(code: str, redirect_uri: str = "") -> str:
    """QQ OAuth2 授权码流程：code 换 token，再取 openid。"""
    cfg = (settings.oauth or {}).get("qq", {})
    appid = cfg.get("appid")
    secret = cfg.get("secret")
    if not appid or not secret:
        raise BizError(ErrorCode.INTERNAL, "QQ OAuth 未配置")
    async with httpx.AsyncClient(timeout=10) as client:
        token_resp = await client.get(
            "https://graph.qq.com/oauth2.0/token",
            params={
                "grant_type": "authorization_code",
                "client_id": appid,
                "client_secret": secret,
                "code": code,
                "redirect_uri": redirect_uri,
            },
        )
        # 返回格式为 urlencoded：access_token=xxx&expires_in=xxx
        body = token_resp.text
        token_map = dict(p.split("=", 1) for p in body.split("&") if "=" in p)
        access_token = token_map.get("access_token")
        if not access_token:
            raise BizError(ErrorCode.UNAUTHORIZED, "QQ 授权失败")
        me_resp = await client.get(
            "https://graph.qq.com/oauth2.0/me",
            params={"access_token": access_token},
        )
        # 返回 callback({ "client_id":"xxx","openid":"xxx" }); 简单解析
        import json
        import re

        m = re.search(r"\{.*\}", me_resp.text)
        if not m:
            raise BizError(ErrorCode.UNAUTHORIZED, "QQ openid 获取失败")
        openid = json.loads(m.group(0)).get("openid")
    if not openid:
        raise BizError(ErrorCode.UNAUTHORIZED, "QQ openid 获取失败")
    return openid


async def wechat_login(db: AsyncSession, code: str) -> tuple[User, bool]:
    """微信登录：code 换 openid，查/建用户并签发。"""
    openid = await _exchange_wechat_openid(code)
    return await _get_or_create_user_by_openid(db, "wechat", openid)


async def qq_login(db: AsyncSession, code: str, redirect_uri: str = "") -> tuple[User, bool]:
    """QQ 登录：code 换 openid，查/建用户并签发。"""
    openid = await _exchange_qq_openid(code, redirect_uri)
    return await _get_or_create_user_by_openid(db, "qq", openid)


async def bind_oauth(
    db: AsyncSession, user: User, provider: str, code: str, redirect_uri: str = ""
) -> None:
    """已登录用户绑定第三方账号；openid 已被他人占用时拒绝并明确提示。"""
    if provider == "wechat":
        openid = await _exchange_wechat_openid(code)
    elif provider == "qq":
        openid = await _exchange_qq_openid(code, redirect_uri)
    else:
        raise BizError(ErrorCode.VALIDATION, "不支持的第三方登录方式")
    acct = await db.scalar(
        select(OAuthAccount).where(
            OAuthAccount.provider == provider,
            OAuthAccount.provider_openid == openid,
        )
    )
    if acct:
        if acct.user_id == user.id:
            raise BizError(ErrorCode.CONFLICT, "该第三方账号已绑定当前账号")
        raise BizError(
            ErrorCode.CONFLICT,
            "该第三方账号已绑定其他账号，请登录原账号解绑后再绑定",
        )
    db.add(OAuthAccount(user_id=user.id, provider=provider, provider_openid=openid))
    await db.commit()
    _logger.info("user_bind_oauth", user_id=str(user.id), provider=provider)
