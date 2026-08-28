"""架构守护：模块导入期不得出现循环依赖。

历史问题：auth 模块曾顶层依赖 admin 模块（共享 DTO），存在循环依赖风险。
本测试在导入期加载关键路由/服务模块，若存在循环依赖会在 import 阶段抛
``ImportError`` / 循环引用，从而在此失败，作为回归守护。
"""

from __future__ import annotations

import importlib


def test_no_circular_import_on_key_modules() -> None:
    # 这些模块若存在导入期循环依赖，会在 import_module 时直接抛错
    for mod in [
        "app.common.schemas",
        "app.modules.auth.router",
        "app.modules.auth.service",
        "app.modules.admin.router",
        "app.modules.admin.service",
        "app.modules.admin.schemas",
    ]:
        importlib.import_module(mod)


def test_auth_no_longer_imports_admin_at_top_level() -> None:
    """auth.router 不应再顶层依赖 admin 模块（共享 DTO 已迁入 common）。"""
    import ast
    import inspect

    import app.modules.auth.router as auth_router

    source = inspect.getsource(auth_router)
    tree = ast.parse(source)
    admin_imports = [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.ImportFrom) and n.module == "app.modules.admin.schemas"
    ]
    assert not admin_imports, "auth.router 仍顶层 import app.modules.admin.schemas"
