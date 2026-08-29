"""跨模块共享的 Pydantic DTO。

放置被多个业务模块共同引用的配置型 schema，避免下层模块（如 auth）为使用一个
共享 DTO 而顶层依赖上层模块（如 admin），从而消除模块间的导入期耦合 / 潜在循环依赖。

例如 ``EmailRegisterConfig`` 同时被认证路由（只读）与管理后台路由（读写）使用，
因此归入公共层，而非 admin 模块。
"""

from __future__ import annotations

from pydantic import BaseModel


class EmailRegisterConfig(BaseModel):
    """邮箱注册规则（后台可动态配置，DB 值覆盖 school.yaml 默认值）。"""

    enabled: bool = True
    domains: list[str] = []
    pattern: str = ""
