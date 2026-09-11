# -*- coding: utf-8 -*-
"""食堂种子数据：按武大实际结构（学部 → 餐饮区 → 食堂）灌入示例数据。

用法:
    # 开发环境（SQLite，自动建表后执行）
    python scripts/seed_canteens.py
    # 仅查看将要写入的内容，不落库
    python scripts/seed_canteens.py --dry-run

幂等：若 canteens 表已有数据则跳过，避免重复灌入。
维度枚举（campuses/zones/types/semesters）直接读取 config/school.yaml 的
canteen 段，与后台 /api/canteens/configs + /api/admin/canteens/config 同源。
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func, select  # noqa: E402

from app.common.models import Base  # noqa: E402
from app.core.database import SessionLocal, engine  # noqa: E402
from app.core.database import _run_sqlite_column_migrations  # noqa: E402
from app.modules.canteen.models import Canteen  # noqa: E402

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCHOOL_YAML = os.path.join(PROJECT_ROOT, "config", "school.yaml")

# 示例食堂：与 school.yaml 中 canteen.zones 的「学部→餐饮区」一一对应。
# 每个 (campus, zone) 下给出若干食堂，含类型/楼层/特色/招牌菜等维度字段。
SEED: list[dict] = [
    # 文理学部
    {
        "campus": "文理学部", "zone": "梅园",
        "name": "梅园食堂", "canteen_type": "学生大伙食堂", "floor": "1F",
        "description": "文理本科生主要食堂，性价比高，早自习顺路。",
        "features": ["便宜", "出餐快", "座位多"], "popular_dishes": ["热干面", "豆皮", "排骨藕汤"],
        "opening_hours": "06:30-21:00",
    },
    {
        "campus": "文理学部", "zone": "梅园",
        "name": "梅园风味食堂", "canteen_type": "风味食堂", "floor": "2F",
        "description": "小炒、麻辣香锅、掉渣饼等风味档口。",
        "features": ["选择多", "可拼桌"], "popular_dishes": ["麻辣香锅", "掉渣饼", "螺蛳粉"],
        "opening_hours": "10:00-21:30",
    },
    {
        "campus": "文理学部", "zone": "桂园",
        "name": "桂园食堂", "canteen_type": "学生大伙食堂", "floor": "1F",
        "description": "桂园片区主力食堂，离图书馆近。",
        "features": ["安静", "便宜"], "popular_dishes": ["三鲜豆皮", "糊汤粉"],
        "opening_hours": "06:30-20:30",
    },
    {
        "campus": "文理学部", "zone": "枫园",
        "name": "枫园食堂", "canteen_type": "学生大伙食堂", "floor": "1F",
        "description": "枫园研究生公寓配套食堂。",
        "features": ["人少", "干净"], "popular_dishes": ["牛肉粉", "蒸菜"],
        "opening_hours": "07:00-20:00",
    },
    # 工学部
    {
        "campus": "工学部", "zone": "湖滨",
        "name": "湖滨食堂", "canteen_type": "学生大伙食堂", "floor": "1F",
        "description": "湖滨片区食堂，靠东湖，环境好。",
        "features": ["湖景", "便宜"], "popular_dishes": ["热干面", "瓦罐汤"],
        "opening_hours": "06:30-21:00",
    },
    {
        "campus": "工学部", "zone": "工学部",
        "name": "工学部食堂", "canteen_type": "学生大伙食堂", "floor": "1F",
        "description": "工学部主食堂，工科生聚集。",
        "features": ["出餐快", "份量大"], "popular_dishes": ["铁板饭", "盖浇饭"],
        "opening_hours": "06:30-20:30",
    },
    {
        "campus": "工学部", "zone": "工学部",
        "name": "工学部风味餐厅", "canteen_type": "风味食堂", "floor": "2F",
        "description": "风味档口，火锅冒菜炸鸡一应俱全。",
        "features": ["夜宵", "选择多"], "popular_dishes": ["冒菜", "炸鸡", "关东煮"],
        "opening_hours": "10:30-22:00",
    },
    {
        "campus": "工学部", "zone": "田园",
        "name": "田园食堂", "canteen_type": "学生大伙食堂", "floor": "1F",
        "description": "田园片区安静食堂。",
        "features": ["人少"], "popular_dishes": ["蒸菜", "套餐饭"],
        "opening_hours": "07:00-20:00",
    },
    # 信息学部
    {
        "campus": "信息学部", "zone": "信息学部",
        "name": "信息学部食堂", "canteen_type": "学生大伙食堂", "floor": "1F",
        "description": "计院/软院学生主食堂。",
        "features": ["便宜", "出餐快"], "popular_dishes": ["黄焖鸡", "牛肉粉"],
        "opening_hours": "06:30-21:00",
    },
    {
        "campus": "信息学部", "zone": "信息学部",
        "name": "信息学部风味食堂", "canteen_type": "风味食堂", "floor": "2F",
        "description": "风味档口，程序员续命咖啡与轻食。",
        "features": ["咖啡", "轻食"], "popular_dishes": ["轻食沙拉", "拿铁"],
        "opening_hours": "08:00-21:00",
    },
    {
        "campus": "信息学部", "zone": "星园",
        "name": "星园食堂", "canteen_type": "学生大伙食堂", "floor": "1F",
        "description": "星园片区食堂，宿舍楼下。",
        "features": ["方便", "便宜"], "popular_dishes": ["热干面", "炒粉"],
        "opening_hours": "06:30-20:30",
    },
    # 医学部
    {
        "campus": "医学部", "zone": "医学部",
        "name": "医学部食堂", "canteen_type": "学生大伙食堂", "floor": "1F",
        "description": "医学部主食堂，靠近一临床。",
        "features": ["便宜", "营养"], "popular_dishes": ["养生汤", "蒸蛋"],
        "opening_hours": "06:30-20:30",
    },
    {
        "campus": "医学部", "zone": "医学部",
        "name": "医学部教工食堂", "canteen_type": "教工食堂", "floor": "3F",
        "description": "教工专属楼层，环境更好。",
        "features": ["安静", "环境好"], "popular_dishes": ["小炒", "套餐"],
        "opening_hours": "11:00-13:30",
    },
]


def load_semester() -> str:
    try:
        with open(SCHOOL_YAML, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        canteen = cfg.get("canteen", {}) or {}
        return str(canteen.get("current_semester") or "")
    except FileNotFoundError:
        return ""


async def seed(dry_run: bool = False) -> None:
    semester = load_semester()
    if not semester:
        print("[warn] school.yaml 未配置 current_semester，semester 字段留空（长期开放）。")

    if dry_run:
        to_create: list[Canteen] = []
        for item in SEED:
            item = dict(item)
            item["semester"] = semester
            to_create.append(Canteen(**item))
        print(f"[dry-run] 将写入 {len(to_create)} 条食堂数据：")
        for c in to_create:
            print(f"  - [{c.campus}/{c.zone}] {c.name} ({c.canteen_type}, {c.floor})")
        return

    # DDL：建表 + 老库补列（与 app 启动时逻辑同源）
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _run_sqlite_column_migrations(conn)

    async with SessionLocal() as db:
        existing = await db.scalar(select(func.count()).select_from(Canteen))
        if existing:
            print(f"[skip] canteens 表已有 {existing} 条数据，跳过种子写入。")
            return

        to_create = [
            Canteen(**{**item, "semester": semester}) for item in SEED
        ]
        db.add_all(to_create)
        await db.commit()
        print(f"[ok] 已写入 {len(to_create)} 条食堂示例数据。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="食堂种子数据灌入")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不落库")
    args = parser.parse_args()
    asyncio.run(seed(dry_run=args.dry_run))
