"""声明式权限作用域（Scope）依赖注入。

为什么需要这一层
----------------
重构前，权限判断以两种形式散落在业务代码里：

* 路由层的 ``require_owner(item.owner_id, user)`` —— 只表达"是不是本人"，
  无法表达"管理员可越权"；
* Service 层理论上不该有权限判断，但一旦需要"管理员可操作他人资源"这类
  规则，就只能在 Service 里写 ``if user.is_admin``，把鉴权耦合进业务。

本模块把"**调用者被允许做什么**"抽象为**作用域（Scope）**，用 FastAPI 的
``Depends`` 在路由层声明式注入。Service 层因此保持零权限耦合：
它只负责"把事情做对"，不再关心"谁有权让我做"。

两套身份体系
------------
本平台存在**两套并存的身份体系**，作用域解析必须同时覆盖：

* ``User``（平台用户）：JWT ``sub`` 为 user.id，以 ``is_admin`` 布尔位标记提权；
* ``AdminUser``（后台管理员）：JWT ``sub`` 为 admin.id，经 ``role_id`` 关联
  ``Role.permissions``（权限码列表）实现 RBAC。

``/api/admin/login`` 签发的是 AdminUser 令牌，其 ``sub`` 在 ``users`` 表里
查不到；反之平台用户登录后也不是 AdminUser。因此解析主体时必须**两边都查**，
只查一边会让其中一套身份彻底失去作用域。

作用域层级
----------
``admin`` ⊃ ``write`` ⊃ ``read``，即管理员自动具备写与读。
``audit`` 是**独立的只读分支**：审计员只能读审计日志，不因"能读"就获得
"能改业务数据"的能力 —— 审计与运营必须职责分离。
"""

from __future__ import annotations

from enum import Enum
from functools import lru_cache

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.exceptions import BizError, ErrorCode
from app.modules.admin.models import AdminUser
from app.modules.auth.models import User


class Scope(str, Enum):
    """权限作用域。

    继承 ``str`` 是为了让 ``Scope.ADMIN == "admin"`` 成立，
    便于与 RBAC 权限码映射表、日志字段、测试断言直接比较。
    """

    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    AUDIT = "audit"


# 作用域蕴含关系（偏序）：持有某作用域即自动持有其全部下游作用域。
# admin 蕴含 write/read；audit 只蕴含 read（不获得写能力）。
_SCOPE_IMPLIES: dict[Scope, frozenset[Scope]] = {
    Scope.READ: frozenset(),
    Scope.WRITE: frozenset({Scope.READ}),
    Scope.ADMIN: frozenset({Scope.READ, Scope.WRITE}),
    Scope.AUDIT: frozenset({Scope.READ}),
}

# RBAC 权限码 → 作用域。
# 来源于 ``Role.permissions``（见 admin.service.ensure_seed 播种的超级管理员权限码）。
# 未登记的权限码不授予任何额外作用域，遵循**最小权限原则**：
# 新增权限码时若不显式登记，默认只得到基础的 read/write。
_PERMISSION_SCOPE_MAP: dict[str, Scope] = {
    "user:view": Scope.READ,
    "report:view": Scope.READ,
    "dashboard:view": Scope.READ,
    "content:audit": Scope.WRITE,
    "report:handle": Scope.WRITE,
    "user:ban": Scope.ADMIN,
    "admin:config": Scope.ADMIN,
    "audit:view": Scope.AUDIT,
    "audit:read": Scope.AUDIT,
    "audit:export": Scope.AUDIT,
}


@lru_cache(maxsize=8)
def _expand(scope: Scope) -> frozenset[Scope]:
    """展开作用域的闭包（含自身及其蕴含的全部下游作用域）。

    结果用 ``lru_cache`` 缓存：作用域集合是编译期常量，无需每次请求重算。
    """
    result = {scope}
    for implied in _SCOPE_IMPLIES.get(scope, frozenset()):
        result |= _expand(implied)
    return frozenset(result)


class Principal:
    """当前请求的安全主体：身份 + 已解析的作用域集合。"""

    __slots__ = ("user_id", "user", "admin", "scopes")

    def __init__(
        self,
        user_id: str,
        user: User | None,
        admin: AdminUser | None,
        scopes: frozenset[Scope],
    ) -> None:
        self.user_id = user_id
        self.user = user
        self.admin = admin
        self.scopes = scopes

    def has(self, scope: Scope | str) -> bool:
        return Scope(scope) in self.scopes

    def __repr__(self) -> str:  # pragma: no cover - 仅调试用
        return (
            f"<Principal user_id={self.user_id!r} "
            f"scopes={sorted(s.value for s in self.scopes)}>"
        )


async def get_principal(
    request: Request, db: AsyncSession = Depends(get_db)
) -> Principal:
    """解析当前请求的安全主体。

    与 ``get_current_user`` 的差异：后者**只认平台用户**，AdminUser 令牌会被
    判为"用户不存在"；本函数同时容纳两套身份，是作用域体系的统一入口。

    FastAPI 的依赖缓存（``use_cache=True``，默认）保证**同一请求内**本函数只
    执行一次，因此路由上叠加多个 ``require_scope`` 不会重复查库。
    """
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise BizError(ErrorCode.UNAUTHORIZED, "未认证或登录已过期")

    # 两套身份都查：AdminUser 的 sub 在 users 表里查不到，反之亦然。
    user = await db.get(User, user_id)
    # AdminUser.role 是普通 lazy 关系，异步上下文里直接访问会抛 MissingGreenlet
    # （隐式 IO 不被允许），必须用 selectinload 显式预载。
    admin = (
        await db.scalars(
            select(AdminUser)
            .where(AdminUser.id == user_id)
            .options(selectinload(AdminUser.role))
        )
    ).first()

    if user is None and admin is None:
        raise BizError(ErrorCode.UNAUTHORIZED, "未认证或登录已过期")
    if user is not None and user.status == 1:  # UserStatus.BANNED
        raise BizError(ErrorCode.FORBIDDEN, "账号已被封禁")
    if admin is not None and admin.disabled:
        raise BizError(ErrorCode.FORBIDDEN, "管理员账号已禁用")

    granted: set[Scope] = set()
    if user is not None:
        granted |= {Scope.READ, Scope.WRITE}
        if user.is_admin:
            granted.add(Scope.ADMIN)
    if admin is not None:
        granted |= {Scope.READ, Scope.WRITE, Scope.ADMIN}
        # 权限码 → 作用域；未登记的权限码不额外授权
        # role_id 为空时直接跳过：既避免无谓查询，也避免触碰关系的惰性加载。
        permissions = (admin.role.permissions if admin.role else None) or []
        for code in permissions:
            mapped = _PERMISSION_SCOPE_MAP.get(str(code))
            if mapped is not None:
                granted.add(mapped)

    # 展开闭包：拿到 admin 即自动具备 write/read
    expanded: set[Scope] = set()
    for scope in granted:
        expanded |= _expand(scope)

    return Principal(user_id=str(user_id), user=user, admin=admin, scopes=frozenset(expanded))


def require_scope(scope: Scope | str):
    """依赖工厂：声明式作用域闸门。

    用法（路由层声明，Service 层零感知）::

        @router.delete("/{item_id}")
        async def delete(..., _: Principal = Depends(require_scope("admin"))):
            ...

    对应 FastAPI 特性：**带参数的依赖**（dependency with parameters）。
    ``require_scope("admin")`` 返回一个闭包，FastAPI 在解析路由时调用它，
    因此同一个工厂可以参数化出任意多个彼此独立的依赖实例。

    :param scope: 所需作用域；``admin`` 隐含 ``write``/``read``。
    :raises BizError: 403 —— 已认证但作用域不足；401 —— 未认证。
    """
    needed = Scope(scope)

    async def _dependency(
        principal: Principal = Depends(get_principal),
    ) -> Principal:
        if not principal.has(needed):
            raise BizError(
                ErrorCode.FORBIDDEN,
                f"需要 {needed.value} 权限",
            )
        return principal

    # 便于测试与 OpenAPI 调试：暴露被校验的作用域
    _dependency.__name__ = f"require_scope_{needed.value}"
    return _dependency


def require_owner_or_scope(
    owner_id: str,
    principal: Principal,
    scope: Scope | str = Scope.ADMIN,
) -> None:
    """资源级归属校验：本人**或**持指定作用域者放行。

    作用域只能表达"调用者是什么角色"，无法表达"这条记录是不是他的"。
    校园场景的真实规则是**二者取或**：

    * 普通用户（``write``）只能删自己的物品；
    * 管理员（``admin``）可以删任何人的物品。

    把它放在路由层的一个函数调用里，Service 层就既不需要知道"谁在操作"，
    也不需要知道"什么是管理员"。

    :param owner_id: 资源归属用户 ID。
    :param principal: 经 ``require_scope`` 校验过的安全主体。
    :param scope: 可越权的作用域，默认 ``admin``。
    :raises BizError: 403 —— 既非本人也无越权作用域。
    """
    if str(owner_id) == str(principal.user_id):
        return
    if principal.has(scope):
        return
    raise BizError(ErrorCode.FORBIDDEN, "无权操作该资源")
