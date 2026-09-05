"""Task 1 单元测试：声明式权限作用域（require_scope）。

覆盖点：
1. 作用域闭包展开（admin ⊃ write ⊃ read；audit 只 ⊃ read）。
2. 两套身份体系（平台 User / 后台 AdminUser）都能解析出主体。
3. 路由层声明式鉴权：越权 403、未认证 401。
4. 校园业务规则：本人可删自己的（write），管理员可删任何人的（admin）。
5. 审计员只能看日志，拿不到 write（职责分离）。
"""

from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.deps import (
    Principal,
    Scope,
    get_principal,
    require_owner_or_scope,
    require_scope,
)
from app.core.exceptions import BizError, ErrorCode


# ---------------------------------------------------------------------------
# 纯函数层：作用域闭包
# ---------------------------------------------------------------------------
def test_admin_implies_write_and_read() -> None:
    """管理员自动具备写与读。"""
    from app.core.deps import _expand

    assert Scope.WRITE in _expand(Scope.ADMIN)
    assert Scope.READ in _expand(Scope.ADMIN)
    assert Scope.AUDIT not in _expand(Scope.ADMIN)


def test_audit_grants_only_read_not_write() -> None:
    """审计员只获得读能力，不得获得写能力（职责分离的核心断言）。"""
    from app.core.deps import _expand

    assert Scope.READ in _expand(Scope.AUDIT)
    assert Scope.WRITE not in _expand(Scope.AUDIT)
    assert Scope.ADMIN not in _expand(Scope.AUDIT)


def test_bottom_scope_has_no_implications() -> None:
    from app.core.deps import _expand

    assert _expand(Scope.READ) == frozenset({Scope.READ})


# ---------------------------------------------------------------------------
# 资源级归属：本人 or 越权作用域
# ---------------------------------------------------------------------------
def _principal(user_id: str, scopes: set[Scope]) -> Principal:
    return Principal(user_id=user_id, user=None, admin=None, scopes=frozenset(scopes))


def test_owner_passes_without_admin_scope() -> None:
    p = _principal("u1", {Scope.READ, Scope.WRITE})
    require_owner_or_scope("u1", p, Scope.ADMIN)  # 不应抛出


def test_non_owner_without_scope_is_forbidden() -> None:
    p = _principal("u1", {Scope.READ, Scope.WRITE})
    with pytest.raises(BizError) as exc:
        require_owner_or_scope("u2", p, Scope.ADMIN)
    assert exc.value.code == ErrorCode.FORBIDDEN


def test_non_owner_with_admin_scope_passes() -> None:
    """校园规则：管理员可以删任何人的物品。"""
    p = _principal("admin-1", {Scope.READ, Scope.WRITE, Scope.ADMIN})
    require_owner_or_scope("u2", p, Scope.ADMIN)  # 不应抛出


# ---------------------------------------------------------------------------
# HTTP 层：依赖注入闸门
# ---------------------------------------------------------------------------
def _build_app(scopes: frozenset[Scope], user_id: str = "u1") -> FastAPI:
    """构造一个只挂载作用域闸门的测试应用，避开数据库与真实鉴权。

    必须注册与生产一致的异常处理器：``BizError`` 若不转成 ApiResponse，
    TestClient 会把异常直接抛出，测试就看不到真实的响应体格式。
    """
    from app.core.exceptions import register_exception_handlers

    app = FastAPI()
    register_exception_handlers(app)

    # 用依赖覆盖把主体解析替换成固定值，聚焦"闸门"本身而非身份来源
    async def _fake_principal() -> Principal:
        return Principal(user_id=user_id, user=None, admin=None, scopes=scopes)

    app.dependency_overrides[get_principal] = _fake_principal

    @app.get("/need-write", dependencies=[Depends(require_scope(Scope.WRITE))])
    async def need_write() -> dict:
        return {"ok": True}

    @app.get("/need-admin", dependencies=[Depends(require_scope("admin"))])
    async def need_admin() -> dict:
        return {"ok": True}

    @app.get("/need-audit", dependencies=[Depends(require_scope("audit"))])
    async def need_audit() -> dict:
        return {"ok": True}

    return app


def test_scope_gate_allows_sufficient_scope() -> None:
    client = TestClient(_build_app(frozenset({Scope.READ, Scope.WRITE})))
    assert client.get("/need-write").status_code == 200


def test_scope_gate_rejects_insufficient_scope_with_biz_code() -> None:
    """越权走统一业务异常：HTTP 200 + code=40300（与全站响应约定一致）。"""
    client = TestClient(_build_app(frozenset({Scope.READ})))
    r = client.get("/need-write")
    assert r.status_code == 200
    assert r.json()["code"] == ErrorCode.FORBIDDEN


def test_admin_scope_satisfies_write_gate() -> None:
    client = TestClient(_build_app(frozenset(_expand_admin())))
    assert client.get("/need-write").status_code == 200
    assert client.get("/need-admin").status_code == 200


def _expand_admin() -> set[Scope]:
    from app.core.deps import _expand

    return set(_expand(Scope.ADMIN))


def test_auditor_cannot_reach_write_gate() -> None:
    """审计员（只有 audit+read）能看日志，但访问写接口应被拒。"""
    from app.core.deps import _expand

    scopes = frozenset(set(_expand(Scope.AUDIT)) | set(_expand(Scope.READ)))
    client = TestClient(_build_app(scopes))

    assert client.get("/need-audit").status_code == 200

    r = client.get("/need-write")
    # 业务错误以 HTTP 200 + code=40300 返回（全站统一约定）
    assert r.json()["code"] == ErrorCode.FORBIDDEN


# ---------------------------------------------------------------------------
# 主体解析：未认证
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_get_principal_rejects_unauthenticated() -> None:
    """request.state 里没有 user_id → 401，且不触碰数据库。"""
    from app.core import deps as deps_module

    class _Req:
        class state:
            user_id = None

    with pytest.raises(BizError) as exc:
        await deps_module.get_principal(_Req(), db=None)  # type: ignore[arg-type]
    assert exc.value.code == ErrorCode.UNAUTHORIZED


@pytest.mark.asyncio
async def test_get_principal_rejects_unknown_identity(monkeypatch) -> None:
    """sub 在 users 与 admin_users 两表里都查不到 → 401（而非漏判为匿名放行）。"""
    from app.core import deps as deps_module

    class _Req:
        class state:
            user_id = "ghost-id"

    class _FakeDB:
        async def get(self, model, pk):
            return None

        async def scalars(self, stmt):
            class _R:
                def first(self):
                    return None

            return _R()

    with pytest.raises(BizError) as exc:
        await deps_module.get_principal(_Req(), db=_FakeDB())  # type: ignore[arg-type]
    assert exc.value.code == ErrorCode.UNAUTHORIZED
