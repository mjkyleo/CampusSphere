"""管理后台路由：/api/admin/*。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
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
    CourseDepartmentsConfig,
    EmailRegisterConfig,
    ItemCategoriesConfig,
    ItemReviewConfig,
    ItemReviewRejectRequest,
)
from app.modules.admin.service import (
    admin_delete_item,
    admin_login,
    admin_update_item,
    approve_item,
    ban_user,
    cleanup_orphan_files,
    dashboard,
    get_course_departments,
    get_email_register_config,
    get_item_categories,
    get_item_review_config,
    get_permissions,
    list_all_items,
    list_orphan_files,
    list_users,
    promote_user_to_admin,
    reject_item,
    unban_user,
    update_course_departments,
    update_email_register_config,
    update_item_categories,
    update_item_review_config,
)
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
    db: AsyncSession = Depends(get_db),
    _gw: None = Depends(require_admin_gateway),
):
    tokens = await admin_login(db, data.username, data.password)
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
