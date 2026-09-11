"""跨数据库可移植的类型封装。

SQLite 与 PostgreSQL 对 JSON 的支持不同（SQLite 无原生 JSONB），为让同一套
模型在开发（SQLite）与生产（PostgreSQL 16）都能跑，这里用 ``TypeDecorator``
把 Python 列表固化为「JSON 文本」存储：SQLite 走 TEXT，PostgreSQL 同样可走
TEXT/JSONB。读写时自动在 ``list`` 与 JSON 字符串间转换，业务层只感知 list。
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import String, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB


class JsonList(TypeDecorator):
    """把 Python list 序列化为 JSON 文本的跨库列类型。

    - 空列表存为 "[]"，绝不为 NULL，避免下游判空还要区分 None/空串。
    - PostgreSQL 下使用 JSONB 以获得原生 JSON 检索能力；其余方言回退到 TEXT。
    """

    cache_ok = True
    impl = String
    # 列表文本最长 65535 字符，足够存放 features / popular_dishes 等标签数组
    length = 65535

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(String(self.length))

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return "[]"
        if isinstance(value, str):
            # 已经是 JSON 串则原样写入（容错，避免双重序列化）
            return value
        return json.dumps(value, ensure_ascii=False)

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is None or value == "":
            return []
        if isinstance(value, list):
            return value
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else [parsed]
        except (json.JSONDecodeError, TypeError):
            return []
