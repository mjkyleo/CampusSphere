"""管理后台业务逻辑：认证、RBAC、封禁、仪表盘。"""

from __future__ import annotations

import secrets
import string
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import ItemStatus, UserStatus
from app.core.config import settings
from app.core.exceptions import BizError, ErrorCode
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.core.storage import storage_client
from app.modules.admin.models import AdminUser, AppConfig, Permission, Role
from app.modules.auth.models import User
from app.modules.canteen.models import Canteen, Dish, Stall
from app.modules.item.models import Item, ItemImage
from app.modules.item.schemas import ItemUpdate
from app.modules.item.service import cas_item_status
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
    """初始化默认角色与管理员（每次启动调用，幂等）。

    账号与密码读取自配置（school.yaml 的 ``admin.bootstrap.*`` 或由 ``.env`` 覆盖），
    不再硬编码于源码。仅当配置未提供密码时，回退到开发/测试用弱口令 ``admin123`` 并告警——
    生产环境必须在配置中指定强密码（由 ``validate_admin_security`` 在启动期拦截弱配置）。

    为什么要**每次启动都同步权限**（而非"管理员已存在就直接返回"）
    -------------------------------------------------------------
    早期版本在管理员已存在时提前 return，导致后续新增的权限码**永远不会**
    落到既有部署的角色上。审计端点改用 ``require_scope("audit")`` 后，
    老库里的 ``super_admin`` 因缺少 ``audit:view`` 会被自己的系统拒之门外——
    一次重启就丢权限，属于典型的"升级即故障"。

    因此这里把「角色/权限同步」与「管理员账号创建」解耦：
    权限同步幂等执行（只增不减），账号创建才受"是否已存在"约束。
    """
    if not settings.admin_bootstrap_enabled:
        _logger.info("admin_seed_disabled")
        return
    username = settings.admin_bootstrap_username or "siteadmin"
    password = settings.admin_bootstrap_password or "admin123"

    # --- 角色与权限：每次启动同步（只增不减，避免回收已授予的能力）---
    role = await _sync_roles(db)

    existing = await db.scalar(select(AdminUser).where(AdminUser.username == username))
    if existing:
        await db.commit()
        return
    # role_id 列类型为 String(36)，直接存入字符串形式的 UUID
    admin = AdminUser(username=username, password_hash=hash_password(password), role_id=role.id)
    db.add(admin)
    await db.commit()
    _logger.info("admin_seeded", username=username, from_config=bool(settings.admin_bootstrap_password))


# 超级管理员权限码。``audit:view`` 必须在此登记：审计端点由
# ``require_scope("audit")`` 把关，缺少该权限码的管理员会被自己的后台挡在门外。
_SUPER_ADMIN_PERMS = [
    "user:ban",
    "user:view",
    "report:handle",
    "content:audit",
    "dashboard:view",
    "audit:view",
]

# 审计员角色：只读审计日志，**不**具备任何写作用域（职责分离）。
# 其权限码映射后只得到 read + audit，拿不到 write/admin。
_AUDITOR_PERMS = ["audit:view", "user:view"]


async def _sync_roles(db: AsyncSession) -> Role:
    """幂等同步内置角色与权限（只增不减），返回 super_admin 角色。

    "只增不减"是刻意的：运维可能手工给角色加过权限，启动时的自动同步若做
    全量覆盖，会把人工调整悄悄抹掉。
    """
    # 去重：audit:view 等权限码同时出现在 _SUPER_ADMIN_PERMS 与 _AUDITOR_PERMS 中。
    # 若会话 autoflush 关闭，第二次遍历的 existence 查询看不到刚 add 的待提交记录，
    # 会再次插入同名权限码，触发 permissions.code 唯一约束冲突并回滚整个 seed，
    # 导致管理员账号（ensure_seed 在 _sync_roles 之后才创建）永远建不出来。
    # 这里用有序集合先去重，从根本上避免重复插入。
    _seen: set[str] = set()
    for code in _SUPER_ADMIN_PERMS + _AUDITOR_PERMS:
        if code in _seen:
            continue
        _seen.add(code)
        if not await db.scalar(select(Permission).where(Permission.code == code)):
            db.add(Permission(name=code, code=code, description=code))
    await db.flush()

    specs = [
        ("super_admin", "超级管理员", _SUPER_ADMIN_PERMS),
        ("auditor", "审计员（只读审计日志）", _AUDITOR_PERMS),
    ]
    result: Role | None = None
    for name, desc, perms in specs:
        role = await db.scalar(select(Role).where(Role.name == name))
        if role is None:
            role = Role(name=name, description=desc, permissions=list(perms))
            db.add(role)
            await db.flush()
        else:
            # 补齐新增权限码，保留既有的人工调整
            merged = list(role.permissions or [])
            for code in perms:
                if code not in merged:
                    merged.append(code)
            role.permissions = merged
        if name == "super_admin":
            result = role
    await db.flush()
    assert result is not None  # 上面循环必然创建/加载 super_admin
    return result


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

    # 复用统一的角色同步，避免这里再维护一份"超级管理员有哪些权限"的副本——
    # 两份清单迟早会漂移，漂移的表现正是"提升上来的管理员比 bootstrapped 的少权限"。
    role = await _sync_roles(db)

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


# ---------------------------------------------------------------------------
# 分类配置化（P1）：job / share / teammate 三类的分类列表
#
# 与 items.categories 走完全相同的四层链路：
#   school.yaml 默认值 → 后台 PUT 写 AppConfig(DB) 覆盖 → 公开 GET 下发
#   → 前端动态拉取 + FALLBACK 兜底
# 之前这三类分类是写死在前端常量里的，运营想改一个分类必须改代码发版。
# ---------------------------------------------------------------------------

_JOB_CATEGORIES_KEY = "job.categories"
_SHARE_CATEGORIES_KEY = "share.categories"
_TEAMMATE_CATEGORIES_KEY = "teammate.categories"

_DEFAULT_JOB_CATEGORIES = [
    "助教/助管", "家教辅导", "校园代理", "技术开发", "设计剪辑", "活动执行", "文案编辑", "其他",
]
_DEFAULT_SHARE_CATEGORIES = [
    "期末复习题", "考研考证", "课件PPT", "实验报告模版", "竞赛真题", "开源代码", "其他",
]
_DEFAULT_TEAMMATE_CATEGORIES = [
    "学术竞赛", "考研考公", "运动健身", "游戏开黑", "旅行逛街", "期末自习", "其他",
]

# (AppConfig key, settings 段名, yaml 字段名, 兜底列表, 中文名, 单条最大长度)
_CATEGORY_SPECS: dict[str, tuple[str, str, str, list[str], str, int]] = {
    "job": (_JOB_CATEGORIES_KEY, "job", "categories", _DEFAULT_JOB_CATEGORIES, "岗位分类", _CONFIG_TAG_MAX_LEN),
    "share": (_SHARE_CATEGORIES_KEY, "share", "categories", _DEFAULT_SHARE_CATEGORIES, "资料分类", _CONFIG_TAG_MAX_LEN),
    "teammate": (_TEAMMATE_CATEGORIES_KEY, "teammate", "categories", _DEFAULT_TEAMMATE_CATEGORIES, "搭子分类", _CONFIG_TAG_MAX_LEN),
}


async def _get_config_categories(db: AsyncSession, scope: str) -> list[str]:
    """读取某个业务域的分类列表：DB（后台配置）优先，缺省回退 school.yaml。"""
    key, section, field, fallback, _name, _maxlen = _CATEGORY_SPECS[scope]
    default = [str(c) for c in ((getattr(settings, section, None) or {}).get(field) or fallback)]
    cfg = await db.scalar(select(AppConfig).where(AppConfig.key == key))
    if not cfg:
        return default
    return [str(c) for c in (cfg.value.get(field) or [])] or default


async def _update_config_categories(db: AsyncSession, scope: str, values: list[str]) -> list[str]:
    """后台更新某个业务域的分类列表（写 DB，实时生效）。"""
    key, _section, field, _fallback, name, maxlen = _CATEGORY_SPECS[scope]
    cleaned = _clean_config_tags(values, name, maxlen)
    payload = {field: cleaned}
    cfg = await db.scalar(select(AppConfig).where(AppConfig.key == key))
    if cfg:
        cfg.value = payload
    else:
        db.add(AppConfig(key=key, value=payload))
    await db.commit()
    _logger.info(f"admin_update_{scope}_categories", categories=cleaned)
    return cleaned


async def get_job_categories(db: AsyncSession) -> list[str]:
    """兼职岗位分类（后台可配置）。"""
    return await _get_config_categories(db, "job")


async def update_job_categories(db: AsyncSession, categories: list[str]) -> list[str]:
    return await _update_config_categories(db, "job", categories)


async def get_share_categories(db: AsyncSession) -> list[str]:
    """学术资料分类（后台可配置）。"""
    return await _get_config_categories(db, "share")


async def update_share_categories(db: AsyncSession, categories: list[str]) -> list[str]:
    return await _update_config_categories(db, "share", categories)


async def get_teammate_categories(db: AsyncSession) -> list[str]:
    """搭子组队分类（后台可配置）。"""
    return await _get_config_categories(db, "teammate")


async def update_teammate_categories(db: AsyncSession, categories: list[str]) -> list[str]:
    return await _update_config_categories(db, "teammate", categories)


async def normalize_category(
    db: AsyncSession, scope: str, value: str, *, empty_ok: bool = True
) -> str:
    """发布时把分类收敛到配置列表内，杜绝脏数据。

    - 命中配置列表 → 原样返回；
    - 未命中（前端写死旧值 / 直接调接口 / 运营删掉了该分类）→ 归入兜底类
      （优先「其他」，其次列表末位），并记 warning 便于运营发现；
    - 空值 → 同样落兜底类，避免出现 category="" 的无法筛选的记录。

    选「归一化」而不是「拒绝」是有意的：分类是运营概念，用户不该为运营
    调整分类而发布失败。
    """
    categories = await _get_config_categories(db, scope)
    fallback = "其他" if "其他" in categories else (categories[-1] if categories else "其他")
    raw = (value or "").strip()
    if not raw:
        if empty_ok:
            return fallback
        raise BizError(ErrorCode.BAD_REQUEST, "请选择分类")
    if raw in categories:
        return raw
    _logger.warning("category_normalized", scope=scope, raw=raw, fallback=fallback)
    return fallback


# ---------------------------------------------------------------------------
# 课程院系分组（P2）
# ---------------------------------------------------------------------------

_COURSE_DEPARTMENT_GROUPS_KEY = "course.department_groups"


def _clean_department_groups(raw: list[dict]) -> list[dict]:
    """清洗院系分组配置：去除空组名/空院系，同名学部合并，院系去重。"""
    merged: dict[str, list[str]] = {}
    for entry in raw or []:
        if not isinstance(entry, dict):
            continue
        group = str(entry.get("group") or "").strip()
        if not group:
            continue
        if len(group) > 30:
            raise BizError(ErrorCode.BAD_REQUEST, f"学部名称「{group}」过长（最多 30 个字符）")
        depts = merged.setdefault(group, [])
        for d in entry.get("departments") or []:
            name = str(d).strip()
            if not name or name in depts:
                continue
            if len(name) > 30:
                raise BizError(ErrorCode.BAD_REQUEST, f"院系名称「{name}」过长（最多 30 个字符）")
            depts.append(name)
    if len(merged) > 20:
        raise BizError(ErrorCode.BAD_REQUEST, f"学部分组数量过多（最多 20 个）")
    return [{"group": g, "departments": d} for g, d in merged.items() if d]


def _yaml_department_groups() -> list[dict]:
    """读取 school.yaml 的 courses.department_groups（含结构校验）。"""
    raw = (settings.courses or {}).get("department_groups") or []
    try:
        return _clean_department_groups(raw)
    except BizError:
        # 配置文件写坏时不应该让站点起不来：忽略分组，回退到扁平院系列表
        _logger.error("course_department_groups_invalid_in_yaml")
        return []


async def get_course_department_groups(db: AsyncSession) -> list[dict]:
    """读取课程院系分组：DB（后台配置）优先，缺省回退 school.yaml。"""
    default = _yaml_department_groups()
    cfg = await db.scalar(
        select(AppConfig).where(AppConfig.key == _COURSE_DEPARTMENT_GROUPS_KEY)
    )
    if not cfg:
        return default
    stored = cfg.value.get("groups") or []
    if not stored:
        return default
    try:
        return _clean_department_groups(stored)
    except BizError:
        _logger.error("course_department_groups_invalid_in_db")
        return default


async def update_course_department_groups(db: AsyncSession, groups: list[dict]) -> list[dict]:
    """后台更新课程院系分组（写 DB，实时生效）。"""
    cleaned = _clean_department_groups(groups)
    payload = {"groups": cleaned}
    cfg = await db.scalar(
        select(AppConfig).where(AppConfig.key == _COURSE_DEPARTMENT_GROUPS_KEY)
    )
    if cfg:
        cfg.value = payload
    else:
        db.add(AppConfig(key=_COURSE_DEPARTMENT_GROUPS_KEY, value=payload))
    await db.commit()
    _logger.info("admin_update_course_department_groups", groups=len(cleaned))
    return cleaned


async def get_course_departments_merged(db: AsyncSession) -> dict:
    """公开端点用：一次性下发「扁平院系 + 学部分组」两种结构。

    - 配了分组：扁平列表 = 组内院系并集（保证前端老代码与筛选逻辑都能用）；
    - 没配分组：扁平列表沿用 courses.departments，groups 为空数组，
      前端自动降级为原来的单排 pill。
    """
    groups = await get_course_department_groups(db)
    if groups:
        flat: list[str] = []
        for g in groups:
            for d in g["departments"]:
                if d not in flat:
                    flat.append(d)
        return {"departments": flat, "groups": groups}
    return {"departments": await get_course_departments(db), "groups": []}


# ---------------------------------------------------------------------------
# 食堂维度配置（P3）：学部 / 餐饮区 / 类型 / 学期
# ---------------------------------------------------------------------------

_CANTEEN_CONFIG_KEY = "canteen.config"

_DEFAULT_CANTEEN_CONFIG: dict = {
    "campuses": ["文理学部", "工学部", "信息学部", "医学部"],
    "zones": {
        "文理学部": ["梅园", "桂园", "枫园"],
        "工学部": ["湖滨", "工学部", "田园"],
        "信息学部": ["信息学部", "星园"],
        "医学部": ["医学部"],
    },
    "types": ["学生大伙食堂", "风味食堂", "教工食堂"],
    "semesters": [],
    "current_semester": "",
}


def _yaml_canteen_config() -> dict:
    raw = settings.canteen or {}
    cfg = dict(_DEFAULT_CANTEEN_CONFIG)
    for field in ("campuses", "types", "semesters"):
        val = raw.get(field)
        if isinstance(val, list) and val:
            cfg[field] = [str(x).strip() for x in val if str(x).strip()]
    zones = raw.get("zones")
    if isinstance(zones, dict) and zones:
        cfg["zones"] = {
            str(k).strip(): [str(x).strip() for x in (v or []) if str(x).strip()]
            for k, v in zones.items()
        }
    if raw.get("current_semester"):
        cfg["current_semester"] = str(raw["current_semester"]).strip()
    return cfg


def _clean_canteen_config(data: dict) -> dict:
    """清洗食堂维度配置，非法输入抛 40000。"""
    cleaned = dict(_DEFAULT_CANTEEN_CONFIG)
    cleaned["campuses"] = _clean_config_tags(data.get("campuses") or [], "学部", 20)
    cleaned["types"] = _clean_config_tags(data.get("types") or [], "食堂类型", 20)
    cleaned["semesters"] = _clean_config_tags(data.get("semesters") or [], "学期", 30)

    zones_raw = data.get("zones") or {}
    zones: dict[str, list[str]] = {}
    if isinstance(zones_raw, dict):
        campuses = cleaned["campuses"]
        for campus, depts in zones_raw.items():
            key = str(campus).strip()
            if not key:
                continue
            # 餐饮区必须挂在已配置的学部下，否则前端 Tab 里会出现孤儿分组
            if campuses and key not in campuses:
                raise BizError(ErrorCode.BAD_REQUEST, f"餐饮区所属学部「{key}」不在学部列表中")
            zones[key] = _clean_config_tags(list(depts or []), "餐饮区", 20)
    cleaned["zones"] = zones

    semester = str(data.get("current_semester") or "").strip()
    if semester and cleaned["semesters"] and semester not in cleaned["semesters"]:
        raise BizError(ErrorCode.BAD_REQUEST, f"当前学期「{semester}」不在学期列表中")
    cleaned["current_semester"] = semester
    return cleaned


async def get_canteen_config(db: AsyncSession) -> dict:
    """读取食堂维度配置：DB（后台配置）优先，缺省回退 school.yaml。"""
    default = _yaml_canteen_config()
    cfg = await db.scalar(select(AppConfig).where(AppConfig.key == _CANTEEN_CONFIG_KEY))
    if not cfg or not cfg.value:
        return default
    merged = dict(default)
    merged.update(cfg.value)
    # 老版本只存了 campuses/zones 时，types 等字段要有值
    for key in ("campuses", "types", "semesters", "zones"):
        if not merged.get(key):
            merged[key] = default[key]
    return merged


async def update_canteen_config(db: AsyncSession, data: dict) -> dict:
    """后台更新食堂维度配置（写 DB，实时生效）。"""
    payload = _clean_canteen_config(data)
    cfg = await db.scalar(select(AppConfig).where(AppConfig.key == _CANTEEN_CONFIG_KEY))
    if cfg:
        cfg.value = payload
    else:
        db.add(AppConfig(key=_CANTEEN_CONFIG_KEY, value=payload))
    await db.commit()
    _logger.info("admin_update_canteen_config", campuses=len(payload["campuses"]))
    return payload

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
        except Exception as exc:
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
        # 复用前台的条件 UPDATE：管理员改状态同样走 CAS，避免与买家抢购
        # 并发时互相覆盖（管理员看到旧页面点"下架"，实际物品已被预订）。
        await db.flush()
        await cas_item_status(db, str(item.id), item.status, data.status)
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
    item.deleted_at = datetime.now(UTC)
    await db.commit()
    _logger.warning("admin_delete_item", item_id=item_id)


async def approve_item(db: AsyncSession, item_id: str) -> Item:
    """审核通过：待审核(PENDING) -> 上架(ON_SALE)。"""
    item = await db.get(Item, item_id)
    if not item or item.deleted_at is not None:
        raise BizError(ErrorCode.NOT_FOUND, "物品不存在")
    if item.status == ItemStatus.PENDING.value:
        validate_transition(item.status, ItemStatus.ON_SALE.value)
        await cas_item_status(
            db, str(item.id), ItemStatus.PENDING.value, ItemStatus.ON_SALE.value,
            message="该物品状态已变更（可能已被其他管理员处理），请刷新后重试",
        )
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
        await cas_item_status(
            db, str(item.id), ItemStatus.PENDING.value, ItemStatus.OFF_SHELF.value,
            message="该物品状态已变更（可能已被其他管理员处理），请刷新后重试",
        )
        await db.commit()
        await db.refresh(item)
        _logger.info("admin_reject_item", item_id=item_id, reason=reason)
    return item
