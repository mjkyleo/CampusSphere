"""安全工具单元测试：密码哈希、JWT 签发/校验、jti 黑名单。

这些是**鉴权体系的地基**，一旦回归会直接导致越权或全员登录失效，
因此这里做穷尽的边界覆盖（含"失败必须安全"的 fail-closed 语义）。
"""

from __future__ import annotations

from datetime import timedelta

import jwt
import pytest

from app.core.security import (
    _create_token,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_token_jti,
    hash_password,
    is_token_revoked,
    revoke_token,
    verify_password,
)

pytestmark = pytest.mark.unit

_USER_ID = "user-abc-001"


# ---------------------------------------------------------------------------
# 密码哈希
# ---------------------------------------------------------------------------
def test_hash_password_verifies_correct_password():
    """正确密码可通过校验。"""
    hashed = hash_password("Str0ng!Pass")
    assert verify_password("Str0ng!Pass", hashed) is True


def test_hash_password_rejects_wrong_password():
    """错误密码被拒绝。"""
    hashed = hash_password("Str0ng!Pass")
    assert verify_password("wrong-pass", hashed) is False


def test_same_password_yields_different_hashes():
    """bcrypt 带随机盐：同一明文两次哈希结果不同（防彩虹表）。"""
    assert hash_password("same") != hash_password("same")


@pytest.mark.parametrize("bad_hash", ["", "not-a-hash", "$2b$invalid"])
def test_verify_password_with_malformed_hash_is_false(bad_hash):
    """哈希是字符串但格式损坏时返回 False 而**不抛异常**（避免 500 与用户枚举）。"""
    assert verify_password("anything", bad_hash) is False


def test_verify_password_with_none_raises_attribute_error():
    """已知边界：``hashed=None`` 会抛 AttributeError（未被 except 捕获）。

    生产环境 ``users.password_hash`` 声明为 NOT NULL，该分支实际不可达；
    此处以测试**固化现状**并标注风险——若将来允许空哈希，需同步加固
    ``verify_password`` 的异常捕获（补 AttributeError）。
    """
    with pytest.raises(AttributeError):
        verify_password("anything", None)


# ---------------------------------------------------------------------------
# JWT 签发与解析
# ---------------------------------------------------------------------------
def test_access_token_payload():
    """access token 携带 sub / jti / type / 过期时间。"""
    token = create_access_token(_USER_ID)
    payload = decode_token(token)
    assert payload["sub"] == _USER_ID
    assert payload["type"] == "access"
    assert payload["jti"]
    assert payload["exp"] > payload["iat"]


def test_refresh_token_type_is_refresh():
    """refresh token 的 type 必须区别于 access（防止刷新令牌当访问令牌用）。"""
    payload = decode_token(create_refresh_token(_USER_ID))
    assert payload["type"] == "refresh"


def test_token_jti_is_unique_per_issuance():
    """每次签发 jti 不同，保证可按 jti 精确吊销单个会话。"""
    a = get_token_jti(create_access_token(_USER_ID))
    b = get_token_jti(create_access_token(_USER_ID))
    assert a and b and a != b


def test_token_jti_can_be_injected_for_testing():
    """支持外部指定 jti（便于确定性测试与按会话吊销）。"""
    token = create_access_token(_USER_ID, jti="fixed-jti-001")
    assert get_token_jti(token) == "fixed-jti-001"


def test_expired_token_raises():
    """过期令牌解码时抛 ExpiredSignatureError。"""
    expired = _create_token(_USER_ID, "access", timedelta(seconds=-1))
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(expired)


def test_tampered_token_raises():
    """签名被篡改 → InvalidSignatureError（验签生效）。"""
    token = create_access_token(_USER_ID)
    header, payload, signature = token.split(".")
    tampered = f"{header}.{payload}.{signature[:-4]}abcd"
    with pytest.raises(jwt.InvalidSignatureError):
        decode_token(tampered)


def test_get_token_jti_on_garbage_returns_none():
    """垃圾输入返回 None 而非抛异常。"""
    assert get_token_jti("garbage") is None
    assert get_token_jti("") is None


# ---------------------------------------------------------------------------
# 令牌吊销（注销 / 黑名单）
# ---------------------------------------------------------------------------
async def test_revoke_token_marks_it_revoked():
    """吊销后 is_token_revoked 返回 True（注销生效）。"""
    token = create_access_token(_USER_ID)
    assert await is_token_revoked(token) is False
    await revoke_token(token)
    assert await is_token_revoked(token) is True


async def test_revoking_one_token_does_not_affect_others():
    """吊销具备粒度：只影响被吊销的那个 jti。"""
    t1 = create_access_token(_USER_ID)
    t2 = create_access_token(_USER_ID)
    await revoke_token(t1)
    assert await is_token_revoked(t1) is True
    assert await is_token_revoked(t2) is False


async def test_is_token_revoked_on_invalid_token_is_fail_closed():
    """无法解析的令牌视为**已吊销**（fail-closed：宁可拒绝也不放行）。"""
    assert await is_token_revoked("garbage-token") is True


async def test_revoke_expired_token_is_noop():
    """吊销已过期令牌不应抛异常（幂等，注销流程无需关心令牌状态）。"""
    expired = _create_token(_USER_ID, "access", timedelta(seconds=-1))
    await revoke_token(expired)  # 不应抛错
    assert await is_token_revoked(expired) is True
