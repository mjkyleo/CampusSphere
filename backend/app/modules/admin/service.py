"""管理后台业务逻辑：认证、RBAC、封禁、仪表盘。"""

from __future__ import annotations

import secrets
import string
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import ItemStatus, UserStatus
from app.core.config import settings
from app.core.exceptions import BizError, ErrorCode
from app.core.logging import get_logger
from app.core.storage import storage_client
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.modules.admin.models import AdminUser, AppConfig, Permission, Role
from app.modules.auth.models import User
from app.modules.canteen.models import Canteen, Dish, Stall
from app.modules.item.models import Item, ItemImage
from app.modules.item.schemas import ItemUpdate
from app.modules.item.statemachine import validate_transition
from app.modules.report.models import Report

_logger = get_logger("admin.service")


async def get_admin(db: AsyncSession, admin_id: str) -> AdminUser:
    admin = await db.get(AdminUser, admin_id)
    if not admin:
        raise BizError(ErrorCode.NOT_FOUND, "管理员不存在")
    return admin


async def admin_login(db: AsyncSession, username: str, password: str) -> dict:
    admin = await db.scalar(select(AdminUser).where(AdminUser.username == username))
    if not admin or not verify_password(password, admin.password_hash) or admin.disabled:
        raise BizError(ErrorCode.UNAUTHORIZED, "管理员账号或密码错误")
    access = create_access_token(str(admin.id))
    refresh = create_refresh_token(str(admin.id))
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}


async def get_permissions(db: AsyncSession, admin: AdminUser) -> list:
    if not admin.role_id:
        return []
    # role_id 为外键列，值已是字符串，直接用于查询
    role = await db.get(Role, admin.role_id)
    return role.permissions if role else []


async def ensure_seed(db: AsyncSession) -> None:
    """初始化默认角色与管理员（首次启动调用）。

    账号与密码读取自配置（school.yaml 的 ``admin.bootstrap.*`` 或由 ``.env`` 覆盖），
    不再硬编码于源码。仅当配置未提供密码时，回退到开发/测试用弱口令 ``admin123`` 并告警——
    生产环境必须在配置中指定强密码（由 ``validate_admin_security`` 在启动期拦截弱配置）。
    """
    if not settings.admin_bootstrap_enabled:
        _logger.info("admin_seed_disabled")
        return
    username = settings.admin_bootstrap_username or "siteadmin"
    password = settings.admin_bootstrap_password or "admin123"
    existing = await db.scalar(select(AdminUser).where(AdminUser.username == username))
    if existing:
        return
    perms = ["user:ban", "user:view", "report:handle", "content:audit", "dashboard:view"]
    for code in perms:
        if not await db.scalar(select(Permission).where(Permission.code == code)):
            db.add(Permission(name=code, code=code, description=code))
    role = Role(name="super_admin", description="超级管理员", permissions=perms)
    db.add(role)
    await db.flush()
    # role_id 列类型为 String(36)，直接存入字符串形式的 UUID
    admin = AdminUser(username=username, password_hash=hash_password(password), role_id=role.id)
    db.add(admin)
    await db.commit()
    _logger.info("admin_seeded", username=username, from_config=bool(settings.admin_bootstrap_password))


def _gen_random_password(length: int = 16) -> str:
    """生成一次性随机强口令（用于未提供密码的提升场景，不回传前端）。"""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


async def promote_user_to_admin(
    db: AsyncSession, user_id: str, password: str, operator: AdminUser
) -> User:
    """将普通用户提升为管理员：标记 ``User.is_admin`` 并创建/更新其后台 AdminUser 登录账号。"""
    user = await db.get(User, user_id)
    if not user:
        raise BizError(ErrorCode.NOT_FOUND, "用户不存在")
    user.is_admin = True

    # 确保存在超级管理员角色
    role = await db.scalar(select(Role).where(Role.name == "super_admin"))
    if not role:
        perms = ["user:ban", "user:view", "report:handle", "content:audit", "dashboard:view"]
        role = Role(name="super_admin", description="超级管理员", permissions=perms)
        db.add(role)
        await db.flush()

    admin_user = await db.scalar(select(AdminUser).where(AdminUser.username == user.username))
    if admin_user:
        if password:
            admin_user.password_hash = hash_password(password)
        admin_user.disabled = False
    else:
        # 后台账号用户名复用平台用户名；未提供密码时生成一次性随机强口令
        pw = password or _gen_random_password()
        admin_user = AdminUser(username=user.username, password_hash=hash_password(pw), role_id=role.id)
        db.add(admin_user)
    await db.commit()
    await db.refresh(user)
    _logger.warning("admin_promote_user", operator=operator.username, target=user.username)
    return user


async def list_users(db: AsyncSession, page: int = 1, page_size: int = 20) -> dict:
    from app.modules.user.service import list_users as user_list

    return await user_list(db, page=page, page_size=page_size)


async def ban_user(db: AsyncSession, user_id: str, reason: str = "") -> User:
    user = await db.get(User, user_id)
    if not user:
        raise BizError(ErrorCode.NOT_FOUND, "用户不存在")
    user.status = UserStatus.BANNED.value
    await db.commit()
    _logger.warning("admin_ban_user", user_id=user_id, reason=reason)
    return user


async def unban_user(db: AsyncSession, user_id: str) -> User:
    user = await db.get(User, user_id)
    if not user:
        raise BizError(ErrorCode.NOT_FOUND, "用户不存在")
    user.status = UserStatus.NORMAL.value
    await db.commit()
    return user


_EMAIL_REGISTER_KEY = "auth.email_register"


async def get_email_register_config(db: AsyncSession) -> dict:
    """读取邮箱注册规则：DB（后台配置）优先，缺省回退 school.yaml。"""
    default = (settings.auth or {}).get("email_register", {}) or {}
    default = {
        "enabled": bool(default.get("enabled", True)),
        "domains": [str(d) for d in (default.get("domains") or [])],
        "pattern": str(default.get("pattern") or ""),
    }
    cfg = await db.scalar(
        select(AppConfig).where(AppConfig.key == _EMAIL_REGISTER_KEY)
    )
    if not cfg:
        return default
    merged = dict(default)
    merged.update({k: cfg.value.get(k, v) for k, v in default.items()})
    return merged


async def update_email_register_config(db: AsyncSession, data: dict) -> dict:
    """后台更新邮箱注册规则（写 DB，实时生效）。"""
    cfg = await db.scalar(
        select(AppConfig).where(AppConfig.key == _EMAIL_REGISTER_KEY)
    )
    payload = {
        "enabled": bool(data.get("enabled", True)),
        "domains": [str(d) for d in (data.get("domains") or [])],
        "pattern": str(data.get("pattern") or ""),
    }
    if cfg:
        cfg.value = payload
    else:
        db.add(AppConfig(key=_EMAIL_REGISTER_KEY, value=payload))
    await db.commit()
    _logger.info("admin_update_email_register", config=payload)
    return payload


_ITEM_REVIEW_KEY = "item.review"


async def get_item_review_config(db: AsyncSession) -> dict:
    """读取物品发布审核开关：DB（后台配置）优先，缺省回退 school.yaml。"""
    default = (settings.items or {}).get("review", {}) or {}
    default = {"enabled": bool(default.get("enabled", False))}
    cfg = await db.scalar(
        select(AppConfig).where(AppConfig.key == _ITEM_REVIEW_KEY)
    )
    if not cfg:
        return default
    merged = dict(default)
    merged.update({k: cfg.value.get(k, v) for k, v in default.items()})
    return merged


async def update_item_review_config(db: AsyncSession, data: dict) -> dict:
    """后台更新发布审核开关（写 DB，实时生效）。"""
    cfg = await db.scalar(
        select(AppConfig).where(AppConfig.key == _ITEM_REVIEW_KEY)
    )
    payload = {"enabled": bool(data.get("enabled", False))}
    if cfg:
        cfg.value = payload
    else:
        db.add(AppConfig(key=_ITEM_REVIEW_KEY, value=payload))
    await db.commit()
    _logger.info("admin_update_item_review", config=payload)
    return payload


_ITEM_CATEGORIES_KEY = "item.categories"

# 兜底分类（school.yaml 与 DB 均未配置时的最小集合）
_DEFAULT_ITEM_CATEGORIES = ["电子产品", "书籍资料", "日用百货", "交通工具", "运动户外", "美妆服饰", "其他"]


async def get_item_categories(db: AsyncSession) -> list[str]:
    """读取二手交易分类：DB（后台配置）优先，缺省回退 school.yaml。"""
    default = [str(c) for c in ((settings.items or {}).get("categories") or _DEFAULT_ITEM_CATEGORIES)]
    cfg = await db.scalar(
        select(AppConfig).where(AppConfig.key == _ITEM_CATEGORIES_KEY)
    )
    if not cfg:
        return default
    return [str(c) for c in (cfg.value.get("categories") or [])] or default


_CONFIG_TAG_MAX_LEN = 20
_CONFIG_TAG_MAX_COUNT = 30


def _clean_config_tags(tags: list[str], name: str, max_len: int) -> list[str]:
    """清洗并校验后台标签类配置（去重、长度、数量限制），非法输入抛 40000。"""
    seen: set[str] = set()
    cleaned: list[str] = []
    for raw in tags or []:
        tag = str(raw).strip()
        if not tag:
            continue
        if tag in seen:
            continue
        if len(tag) > max_len:
            raise BizError(ErrorCode.BAD_REQUEST, f"{name}「{tag}」名称过长（最多 {max_len} 个字符）")
        seen.add(tag)
        cleaned.append(tag)
    if len(cleaned) > _CONFIG_TAG_MAX_COUNT:
        raise BizError(ErrorCode.BAD_REQUEST, f"{name}数量过多（最多 {_CONFIG_TAG_MAX_COUNT} 个）")
    return cleaned


async def update_item_categories(db: AsyncSession, categories: list[str]) -> list[str]:
    """后台更新二手交易分类（写 DB，实时生效）。"""
    cleaned = _clean_config_tags(categories, "分类", _CONFIG_TAG_MAX_LEN)
    payload = {"categories": cleaned}
    cfg = await db.scalar(
        select(AppConfig).where(AppConfig.key == _ITEM_CATEGORIES_KEY)
    )
    if cfg:
        cfg.value = payload
    else:
        db.add(AppConfig(key=_ITEM_CATEGORIES_KEY, value=payload))
    await db.commit()
    _logger.info("admin_update_item_categories", categories=cleaned)
    return cleaned


_COURSE_DEPARTMENTS_KEY = "course.departments"

# 兜底院系（school.yaml 与 DB 均未配置时的最小集合）
_DEFAULT_COURSE_DEPARTMENTS = [
    "计算机学院", "软件学院", "数学科学学院", "经济管理学院", "外国语学院", "通识教育中心",
]


async def get_course_departments(db: AsyncSession) -> list[str]:
    """读取课程院系列表：DB（后台配置）优先，缺省回退 school.yaml。"""
    default = [str(d) for d in ((settings.courses or {}).get("departments") or _DEFAULT_COURSE_DEPARTMENTS)]
    cfg = await db.scalar(
        select(AppConfig).where(AppConfig.key == _COURSE_DEPARTMENTS_KEY)
    )
    if not cfg:
        return default
    return [str(d) for d in (cfg.value.get("departments") or [])] or default


async def update_course_departments(db: AsyncSession, departments: list[str]) -> list[str]:
    """后台更新课程院系列表（写 DB，实时生效）。"""
    cleaned = _clean_config_tags(departments, "院系", 30)
    payload = {"departments": cleaned}
    cfg = await db.scalar(
        select(AppConfig).where(AppConfig.key == _COURSE_DEPARTMENTS_KEY)
    )
    if cfg:
        cfg.value = payload
    else:
        db.add(AppConfig(key=_COURSE_DEPARTMENTS_KEY, value=payload))
    await db.commit()
    _logger.info("admin_update_course_departments", departments=cleaned)
    return cleaned


# ------------------------------------------------------------------
# 孤儿文件扫描与清理
# ------------------------------------------------------------------


async def _collect_image_refs(db: AsyncSession) -> list[str]:
    """收集所有业务记录引用的图片字符串（object_key 或含 object_key 的 URL）。"""
    refs: list[str] = []
    stmts = [
        select(ItemImage.object_key),
        select(Canteen.image),
        select(Stall.image),
        select(Dish.image),
    ]
    for stmt in stmts:
        rows = await db.execute(stmt)
        for (val,) in rows.all():
            if val:
                refs.append(str(val))
    return refs


async def list_orphan_files(db: AsyncSession) -> dict:
    """扫描存储中未被任何业务记录引用的孤儿文件（只列出，不删除）。"""
    keys = storage_client.list_keys()
    if not keys:
        return {"files": [], "total": 0}
    refs = await _collect_image_refs(db)
    orphans = [
        {"key": f["key"], "size": f["size"]}
        for f in keys
        if not any(f["key"] in ref for ref in refs)
    ]
    _logger.info("admin_list_orphan_files", scanned=len(keys), orphan=len(orphans))
    return {"files": orphans, "total": len(orphans)}


async def cleanup_orphan_files(db: AsyncSession) -> dict:
    """删除全部孤儿文件，返回实际删除数量（单文件失败不中断，记 warning 日志）。"""
    data = await list_orphan_files(db)
    removed = 0
    for f in data["files"]:
        try:
            storage_client.remove_key(f["key"])
            removed += 1
        except Exception as exc:  # noqa: BLE001
            _logger.warning("orphan_remove_failed", key=f["key"], error=str(exc))
    _logger.info("admin_cleanup_orphan_files", removed=removed)
    return {"removed": removed}


async def dashboard(db: AsyncSession) -> dict:
    user_count = await db.scalar(select(func.count()).select_from(User))
    item_count = await db.scalar(select(func.count()).select_from(Item))
    report_count = await db.scalar(select(func.count()).select_from(Report))
    pending_report = await db.scalar(
        select(func.count()).select_from(Report).where(Report.status == 0)
    )
    banned = await db.scalar(select(func.count()).select_from(User).where(User.status == UserStatus.BANNED.value))
    return {
        "users": int(user_count or 0),
        "items": int(item_count or 0),
        "reports": int(report_count or 0),
        "pending_reports": int(pending_report or 0),
        "banned_users": int(banned or 0),
    }


# ------------------------------------------------------------------
# Admin item management (bypasses owner checks)
# ------------------------------------------------------------------


async def list_all_items(
    db: AsyncSession,
    status: int | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """List all items (any user's) with optional status filter and pagination."""
    stmt = select(Item).where(Item.deleted_at.is_(None))
    if status is not None:
        stmt = stmt.where(Item.status == status)
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = (
        await db.scalars(
            stmt.order_by(Item.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    items = [
        {
            "id": str(i.id),
            "owner_id": i.owner_id,
            "title": i.title,
            "description": i.description,
            "price": i.price,
            "category": i.category,
            "status": i.status,
            "images": [
                {"object_key": im.object_key, "sort_order": im.sort_order}
                for im in i.images
            ],
            "created_at": i.created_at.isoformat() if i.created_at else "",
        }
        for i in rows
    ]
    return {"items": items, "total": total or 0, "page": page, "page_size": page_size}


async def admin_update_item(db: AsyncSession, item_id: str, data: ItemUpdate) -> Item:
    """Update any item's fields (bypasses the owner check).

    Used by admins to take items off sale (status=1), edit titles, etc.
    """
    item = await db.get(Item, item_id)
    if not item or item.deleted_at is not None:
        raise BizError(ErrorCode.NOT_FOUND, "物品不存在")
    if data.title is not None:
        item.title = data.title
    if data.description is not None:
        item.description = data.description
    if data.price is not None:
        item.price = data.price
    if data.category is not None:
        item.category = data.category
    if data.status is not None and data.status != item.status:
        item.status = data.status
    await db.commit()
    await db.refresh(item)
    _logger.info("admin_update_item", item_id=item_id, status=item.status)
    return item


async def admin_delete_item(db: AsyncSession, item_id: str) -> None:
    """Soft-delete any item (bypasses the owner check).

    Sets `deleted_at` so the item disappears from listings and detail
    queries but remains in the database for audit purposes.
    """
    item = await db.get(Item, item_id)
    if not item or item.deleted_at is not None:
        raise BizError(ErrorCode.NOT_FOUND, "物品不存在")
    item.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    _logger.warning("admin_delete_item", item_id=item_id)


async def approve_item(db: AsyncSession, item_id: str) -> Item:
    """审核通过：待审核(PENDING) -> 上架(ON_SALE)。"""
    item = await db.get(Item, item_id)
    if not item or item.deleted_at is not None:
        raise BizError(ErrorCode.NOT_FOUND, "物品不存在")
    if item.status == ItemStatus.PENDING.value:
        validate_transition(item.status, ItemStatus.ON_SALE.value)
        item.status = ItemStatus.ON_SALE.value
        await db.commit()
        await db.refresh(item)
        _logger.info("admin_approve_item", item_id=item_id)
    return item


async def reject_item(db: AsyncSession, item_id: str, reason: str = "") -> Item:
    """审核拒绝：待审核(PENDING) -> 下架(OFF_SHELF)。"""
    item = await db.get(Item, item_id)
    if not item or item.deleted_at is not None:
        raise BizError(ErrorCode.NOT_FOUND, "物品不存在")
    if item.status == ItemStatus.PENDING.value:
        validate_transition(item.status, ItemStatus.OFF_SHELF.value)
        item.status = ItemStatus.OFF_SHELF.value
        await db.commit()
        await db.refresh(item)
        _logger.info("admin_reject_item", item_id=item_id, reason=reason)
    return item
