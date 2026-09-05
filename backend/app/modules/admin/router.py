"""管理后台路由：/api/admin/*。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import BizError
from app.core.response import ApiResponse
from app.modules.admin.deps import get_current_admin, require_admin
from app.modules.admin.gateway import gateway_enforced, issue_gateway_token, require_admin_gateway
from app.modules.admin.models import AdminUser
from app.modules.admin.schemas import (
    AdminDiscoverRequest,
    AdminLoginRequest,
    AdminOut,
    AdminPromoteRequest,
    AdminTokenResponse,
    AiFeatureConfig,
    BanRequest,
    CanteenConfig,
    CourseDepartmentGroupsConfig,
    CourseDepartmentsConfig,
    EmailRegisterConfig,
    ItemCategoriesConfig,
    ItemReviewConfig,
    ItemReviewRejectRequest,
    JobCategoriesConfig,
    ShareCategoriesConfig,
    TeammateCategoriesConfig,
)
from app.modules.admin.service import (
    admin_delete_item,
    admin_login,
    admin_update_item,
    approve_item,
    ban_user,
    cleanup_orphan_files,
    dashboard,
    get_canteen_config,
    get_course_department_groups,
    get_course_departments,
    get_email_register_config,
    get_item_categories,
    get_item_review_config,
    get_job_categories,
    get_permissions,
    get_share_categories,
    get_teammate_categories,
    list_all_items,
    list_orphan_files,
    list_users,
    promote_user_to_admin,
    reject_item,
    unban_user,
    update_canteen_config,
    update_course_department_groups,
    update_course_departments,
    update_email_register_config,
    update_item_categories,
    update_item_review_config,
    update_job_categories,
    update_share_categories,
    update_teammate_categories,
)
from app.modules.audit.actions import ActorType, AuditAction, AuditResult
from app.modules.audit.service import record_audit_log
from app.modules.canteen.schemas import CanteenCreate, CanteenOut, DishCreate, DishOut, StallCreate, StallOut
from app.modules.canteen.service import (
    create_canteen,
    create_dish,
    create_stall,
    delete_canteen,
    delete_dish,
    delete_stall,
    list_canteens,
    update_canteen,
    update_dish,
    update_stall,
)
from app.modules.item.schemas import ItemOut, ItemUpdate
from app.modules.report.service import list_reports

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/discover", response_model=ApiResponse[dict])
async def discover(data: AdminDiscoverRequest):
    """用网关密钥换取短时网关令牌（HMAC）。密钥错误一律 404，避免暴露管理端存在。"""
    if gateway_enforced() and (
        not settings.admin_gateway_key or data.gateway_key != settings.admin_gateway_key
    ):
        raise HTTPException(status_code=404, detail="Not Found")
    return ApiResponse.ok(data={"gateway_token": issue_gateway_token()})


@router.post("/login", response_model=ApiResponse[AdminTokenResponse])
async def login(
    data: AdminLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _gw: None = Depends(require_admin_gateway),
):
    try:
        tokens = await admin_login(db, data.username, data.password)
    except BizError as exc:
        # 管理员登录失败属于高危事件（撞库/越权尝试），必须留痕
        await record_audit_log(
            action=AuditAction.ADMIN_LOGIN_FAILED,
            actor_type=ActorType.ADMIN,
            actor_label=data.username,
            result=AuditResult.FAILURE,
            detail={"reason": exc.message},
            request=request,
        )
        raise
    await record_audit_log(
        action=AuditAction.ADMIN_LOGIN,
        actor_type=ActorType.ADMIN,
        actor_label=data.username,
        request=request,
    )
    return ApiResponse.ok(data=AdminTokenResponse(**tokens))


@router.get("/me", response_model=ApiResponse[AdminOut])
async def me(db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    perms = await get_permissions(db, admin)
    out = AdminOut.model_validate(admin)
    out.permissions = perms
    return ApiResponse.ok(data=out)


@router.get("/dashboard", response_model=ApiResponse[dict])
async def dashboard_view(db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    return ApiResponse.ok(data=await dashboard(db))


@router.get("/users", response_model=ApiResponse[dict])
async def users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    return ApiResponse.ok(data=await list_users(db, page=page, page_size=page_size))


@router.post("/users/{user_id}/ban", response_model=ApiResponse[dict])
async def ban(user_id: str, data: BanRequest, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    user = await ban_user(db, user_id, data.reason)
    return ApiResponse.ok(data={"id": str(user.id), "status": user.status})


@router.post("/users/{user_id}/unban", response_model=ApiResponse[dict])
async def unban(user_id: str, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    user = await unban_user(db, user_id)
    return ApiResponse.ok(data={"id": str(user.id), "status": user.status})


@router.post("/users/{user_id}/promote", response_model=ApiResponse[dict])
async def promote(
    user_id: str,
    data: AdminPromoteRequest,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
):
    """将普通用户提升为管理员（设置其后台登录密码），并标记 User.is_admin。"""

    user = await promote_user_to_admin(db, user_id, data.password, admin)
    return ApiResponse.ok(data={"id": str(user.id), "is_admin": user.is_admin})


@router.get("/auth/email-config", response_model=ApiResponse[EmailRegisterConfig])
async def get_email_config(db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    return ApiResponse.ok(data=await get_email_register_config(db))


@router.put("/auth/email-config", response_model=ApiResponse[EmailRegisterConfig])
async def put_email_config(
    data: EmailRegisterConfig, db: AsyncSession = Depends(get_db), _=Depends(require_admin)
):
    payload = await update_email_register_config(db, data.model_dump())
    return ApiResponse.ok(data=EmailRegisterConfig(**payload))


@router.get("/reports", response_model=ApiResponse[dict])
async def reports(
    status: int = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    data = await list_reports(db, status=status if status is not None else None, page=page, page_size=page_size)
    return ApiResponse.ok(data=data)

# ------------------------------------------------------------------
# Admin item management (bypasses owner checks)
# ------------------------------------------------------------------


@router.get("/items", response_model=ApiResponse[dict])
async def admin_list_items(
    status: int = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    """List all items (any user's) with optional status filter and pagination."""
    data = await list_all_items(db, status=status if status is not None else None, page=page, page_size=page_size)
    return ApiResponse.ok(data=data)

# NOTE: 静态路径 /items/review-config 必须先于动态路径 /items/{item_id} 声明，
# 否则 "review-config" 会被当作 item_id 匹配。
@router.get("/items/review-config", response_model=ApiResponse[ItemReviewConfig])
async def admin_get_item_review(db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    return ApiResponse.ok(data=ItemReviewConfig(**await get_item_review_config(db)))


@router.put("/items/review-config", response_model=ApiResponse[ItemReviewConfig])
async def admin_put_item_review(
    data: ItemReviewConfig, db: AsyncSession = Depends(get_db), _=Depends(require_admin)
):
    payload = await update_item_review_config(db, data.model_dump())
    return ApiResponse.ok(data=ItemReviewConfig(**payload))


@router.get("/items/categories", response_model=ApiResponse[ItemCategoriesConfig])
async def admin_get_item_categories(db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    """读取二手交易分类（后台配置）。"""
    return ApiResponse.ok(data=ItemCategoriesConfig(categories=await get_item_categories(db)))


@router.put("/items/categories", response_model=ApiResponse[ItemCategoriesConfig])
async def admin_put_item_categories(
    data: ItemCategoriesConfig, db: AsyncSession = Depends(get_db), _=Depends(require_admin)
):
    """更新二手交易分类（写 DB，实时生效）。"""
    payload = await update_item_categories(db, data.categories)
    return ApiResponse.ok(data=ItemCategoriesConfig(categories=payload))


@router.get("/courses/departments", response_model=ApiResponse[CourseDepartmentsConfig])
async def admin_get_course_departments(db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    """读取课程开课院系列表（后台配置）。"""
    return ApiResponse.ok(data=CourseDepartmentsConfig(departments=await get_course_departments(db)))


@router.put("/courses/departments", response_model=ApiResponse[CourseDepartmentsConfig])
async def admin_put_course_departments(
    data: CourseDepartmentsConfig, db: AsyncSession = Depends(get_db), _=Depends(require_admin)
):
    """更新课程开课院系列表（写 DB，实时生效）。"""
    payload = await update_course_departments(db, data.departments)
    return ApiResponse.ok(data=CourseDepartmentsConfig(departments=payload))


@router.get("/courses/departments/groups", response_model=ApiResponse[CourseDepartmentGroupsConfig])
async def admin_get_course_department_groups(
    db: AsyncSession = Depends(get_db), _=Depends(require_admin)
):
    """读取课程院系的**学部分组**（后台可配置，前端两级筛选的数据源）。"""
    return ApiResponse.ok(data=CourseDepartmentGroupsConfig(groups=await get_course_department_groups(db)))


@router.put("/courses/departments/groups", response_model=ApiResponse[CourseDepartmentGroupsConfig])
async def admin_put_course_department_groups(
    data: CourseDepartmentGroupsConfig, db: AsyncSession = Depends(get_db), _=Depends(require_admin)
):
    """更新课程院系学部分组（写 DB，实时生效）。

    传空数组即可回到"扁平院系"模式（前端降级为单排 pill）。
    """
    payload = await update_course_department_groups(db, [g.model_dump() for g in data.groups])
    return ApiResponse.ok(data=CourseDepartmentGroupsConfig(groups=payload))


# ------------------------------------------------------------------
# 分类配置化（P1）：兼职 / 资料 / 搭子 的分类列表
# 与 items.categories 完全同构：school.yaml 默认值 → DB 覆盖 → 公开端点下发
# ------------------------------------------------------------------


@router.get("/jobs/categories", response_model=ApiResponse[JobCategoriesConfig])
async def admin_get_job_categories(db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    """读取兼职岗位分类（后台配置）。"""
    return ApiResponse.ok(data=JobCategoriesConfig(categories=await get_job_categories(db)))


@router.put("/jobs/categories", response_model=ApiResponse[JobCategoriesConfig])
async def admin_put_job_categories(
    data: JobCategoriesConfig, db: AsyncSession = Depends(get_db), _=Depends(require_admin)
):
    """更新兼职岗位分类（写 DB，实时生效）。"""
    return ApiResponse.ok(data=JobCategoriesConfig(categories=await update_job_categories(db, data.categories)))


@router.get("/shares/categories", response_model=ApiResponse[ShareCategoriesConfig])
async def admin_get_share_categories(db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    """读取学术资料分类（后台配置）。"""
    return ApiResponse.ok(data=ShareCategoriesConfig(categories=await get_share_categories(db)))


@router.put("/shares/categories", response_model=ApiResponse[ShareCategoriesConfig])
async def admin_put_share_categories(
    data: ShareCategoriesConfig, db: AsyncSession = Depends(get_db), _=Depends(require_admin)
):
    """更新学术资料分类（写 DB，实时生效）。"""
    return ApiResponse.ok(data=ShareCategoriesConfig(categories=await update_share_categories(db, data.categories)))


@router.get("/teammates/categories", response_model=ApiResponse[TeammateCategoriesConfig])
async def admin_get_teammate_categories(db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    """读取搭子组队分类（后台配置）。"""
    return ApiResponse.ok(data=TeammateCategoriesConfig(categories=await get_teammate_categories(db)))


@router.put("/teammates/categories", response_model=ApiResponse[TeammateCategoriesConfig])
async def admin_put_teammate_categories(
    data: TeammateCategoriesConfig, db: AsyncSession = Depends(get_db), _=Depends(require_admin)
):
    """更新搭子组队分类（写 DB，实时生效）。"""
    return ApiResponse.ok(data=TeammateCategoriesConfig(categories=await update_teammate_categories(db, data.categories)))


# ------------------------------------------------------------------
# 食堂维度配置（P3）：学部 / 餐饮区 / 类型 / 学期
# ------------------------------------------------------------------


@router.get("/canteens/config", response_model=ApiResponse[CanteenConfig])
async def admin_get_canteen_config(db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    """读取食堂维度枚举（学部 / 餐饮区 / 类型 / 学期）。"""
    return ApiResponse.ok(data=CanteenConfig(**await get_canteen_config(db)))


@router.put("/canteens/config", response_model=ApiResponse[CanteenConfig])
async def admin_put_canteen_config(
    data: CanteenConfig, db: AsyncSession = Depends(get_db), _=Depends(require_admin)
):
    """更新食堂维度枚举（写 DB，实时生效）。"""
    return ApiResponse.ok(data=CanteenConfig(**await update_canteen_config(db, data.model_dump())))

# ------------------------------------------------------------------
# AI 智能助手功能开关（复用 ai 模块的配置读写，与 review-config 同一模式）
# ------------------------------------------------------------------


@router.get("/ai/config", response_model=ApiResponse[dict])
async def admin_get_ai_config(db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    """读取 AI 助手开关与运行状态（含 API Key 配置提示，不回传 Key 本身）。"""
    from app.modules.ai.service import get_ai_feature_config, get_ai_status

    cfg = await get_ai_feature_config(db)
    status = await get_ai_status(db)
    return ApiResponse.ok(data={**cfg, "status": status})


@router.put("/ai/config", response_model=ApiResponse[AiFeatureConfig])
async def admin_put_ai_config(
    data: AiFeatureConfig, db: AsyncSession = Depends(get_db), _=Depends(require_admin)
):
    """更新 AI 助手开关与模型名（写 DB，实时生效）。"""
    from app.modules.ai.service import update_ai_feature_config

    payload = await update_ai_feature_config(db, data.model_dump())
    return ApiResponse.ok(data=AiFeatureConfig(**payload))

# ------------------------------------------------------------------
# Canteen management (admin CRUD: canteens / stalls / dishes)
# ------------------------------------------------------------------
@router.get("/canteens", response_model=ApiResponse[list])
async def admin_list_canteens(db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    """食堂管理列表（含档口与菜品）。"""
    return ApiResponse.ok(data=await list_canteens(db))


@router.post("/canteens", response_model=ApiResponse[CanteenOut])
async def admin_create_canteen(
    data: CanteenCreate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)
):
    return ApiResponse.ok(data=CanteenOut.model_validate(await create_canteen(db, data)))


@router.put("/canteens/{canteen_id}", response_model=ApiResponse[CanteenOut])
async def admin_update_canteen(
    canteen_id: str, data: CanteenCreate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)
):
    return ApiResponse.ok(data=CanteenOut.model_validate(await update_canteen(db, canteen_id, data)))


@router.delete("/canteens/{canteen_id}", response_model=ApiResponse[None])
async def admin_delete_canteen(canteen_id: str, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    """删除食堂（级联删除档口、菜品与评价）。"""
    await delete_canteen(db, canteen_id)
    return ApiResponse.ok(message="已删除")


@router.post("/canteens/stalls", response_model=ApiResponse[StallOut])
async def admin_create_stall(
    data: StallCreate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)
):
    return ApiResponse.ok(data=StallOut.model_validate(await create_stall(db, data)))


@router.put("/canteens/stalls/{stall_id}", response_model=ApiResponse[StallOut])
async def admin_update_stall(
    stall_id: str, data: StallCreate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)
):
    return ApiResponse.ok(data=StallOut.model_validate(await update_stall(db, stall_id, data)))


@router.delete("/canteens/stalls/{stall_id}", response_model=ApiResponse[None])
async def admin_delete_stall(stall_id: str, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    await delete_stall(db, stall_id)
    return ApiResponse.ok(message="已删除")


@router.post("/canteens/dishes", response_model=ApiResponse[DishOut])
async def admin_create_dish(
    data: DishCreate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)
):
    return ApiResponse.ok(data=DishOut.model_validate(await create_dish(db, data)))


@router.put("/canteens/dishes/{dish_id}", response_model=ApiResponse[DishOut])
async def admin_update_dish(
    dish_id: str, data: DishCreate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)
):
    return ApiResponse.ok(data=DishOut.model_validate(await update_dish(db, dish_id, data)))


@router.delete("/canteens/dishes/{dish_id}", response_model=ApiResponse[None])
async def admin_delete_dish(dish_id: str, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    await delete_dish(db, dish_id)
    return ApiResponse.ok(message="已删除")


@router.patch("/items/{item_id}", response_model=ApiResponse[ItemOut])
async def admin_update_item_view(
    item_id: str,
    data: ItemUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    """Update any item's fields (e.g., take off sale). Bypasses owner check."""
    item = await admin_update_item(db, item_id, data)
    return ApiResponse.ok(data=ItemOut.model_validate(item))


@router.delete("/items/{item_id}", response_model=ApiResponse[None])
async def admin_delete_item_view(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    """Soft-delete any item. Bypasses owner check."""
    await admin_delete_item(db, item_id)
    return ApiResponse.ok(message="已删除")


@router.post("/items/{item_id}/approve", response_model=ApiResponse[ItemOut])
async def admin_approve_item_view(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    """审核通过：待审核(PENDING) -> 上架(ON_SALE)。"""
    item = await approve_item(db, item_id)
    return ApiResponse.ok(data=ItemOut.model_validate(item))


@router.post("/items/{item_id}/reject", response_model=ApiResponse[ItemOut])
async def admin_reject_item_view(
    item_id: str,
    data: ItemReviewRejectRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    """审核拒绝：待审核(PENDING) -> 下架(OFF_SHELF)。"""
    item = await reject_item(db, item_id, reason=data.reason)
    return ApiResponse.ok(data=ItemOut.model_validate(item))


@router.post("/config/reload", response_model=ApiResponse[dict])
async def reload_school_config(_=Depends(require_admin)):
    """重读 ``config/school.yaml`` 并广播到所有实例（零停机热更新）。

    适用场景：运维直接修改了服务器上的 school.yaml（学校名称、域名白名单、
    业务规则阈值等静态配置），希望**不重启**就让全校实例生效。

    实现：向 Redis ``config:reload`` 频道发布消息，各实例的长驻监听 Task
    收到后原地刷新 ``Settings`` 单例。发布者自身也在订阅者之列，
    因此本实例同样会刷新。

    Redis 不可用（``receivers == 0``）时降级为**仅本机刷新**并置
    ``degraded=true`` —— 让运维立刻看到"热更新没广播出去"，
    而不是误以为全集群已生效。
    """
    from app.core.config_reload import publish_config_reload, reload_settings

    receivers = await publish_config_reload(reason="admin:config-reload")
    degraded = receivers == 0
    if degraded:
        # 无 Redis：至少让本机生效，避免管理员的操作被完全吞掉
        await reload_settings(reason="admin:config-reload:local-only")
    return ApiResponse.ok(
        data={"receivers": receivers, "degraded": degraded},
        message="已广播配置重载" if not degraded else "Redis 不可用，仅本机已刷新",
    )


@router.get("/files/orphans", response_model=ApiResponse[dict])
async def admin_list_orphan_files_view(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    """扫描存储中未被任何业务记录引用的孤儿文件（只列出，不删除）。"""
    data = await list_orphan_files(db)
    return ApiResponse.ok(data=data)


@router.delete("/files/orphans", response_model=ApiResponse[dict])
async def admin_cleanup_orphan_files_view(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    """删除全部孤儿文件，返回实际删除数量。"""
    data = await cleanup_orphan_files(db)
    return ApiResponse.ok(data=data, message=f"已清理 {data['removed']} 个孤儿文件")
