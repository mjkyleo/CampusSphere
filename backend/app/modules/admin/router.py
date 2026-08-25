"""管理后台路由：/api/admin/*。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import BizError, ErrorCode
from app.core.response import ApiResponse
from app.modules.admin.schemas import (
    AdminLoginRequest,
    AdminOut,
    AdminTokenResponse,
    BanRequest,
    EmailRegisterConfig,
    ItemReviewConfig,
    ItemReviewRejectRequest,
)
from app.modules.admin.service import (
    admin_delete_item,
    admin_login,
    admin_update_item,
    approve_item,
    ban_user,
    dashboard,
    ensure_seed,
    get_admin,
    get_email_register_config,
    get_item_review_config,
    get_permissions,
    list_all_items,
    list_users,
    reject_item,
    unban_user,
    update_email_register_config,
    update_item_review_config,
)
from app.modules.item.schemas import ItemOut, ItemUpdate
from app.modules.report.service import list_reports

router = APIRouter(prefix="/api/admin", tags=["admin"])


async def get_current_admin(request: Request, db: AsyncSession = Depends(get_db)):
    admin_id = getattr(request.state, "user_id", None)
    if not admin_id:
        raise BizError(ErrorCode.UNAUTHORIZED, "管理员未认证")
    admin = await get_admin(db, admin_id)
    if admin.disabled:
        raise BizError(ErrorCode.FORBIDDEN, "账号已禁用")
    return admin


@router.post("/login", response_model=ApiResponse[AdminTokenResponse])
async def login(data: AdminLoginRequest, db: AsyncSession = Depends(get_db)):
    tokens = await admin_login(db, data.username, data.password)
    return ApiResponse.ok(data=AdminTokenResponse(**tokens))


@router.get("/me", response_model=ApiResponse[AdminOut])
async def me(db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    perms = await get_permissions(db, admin)
    out = AdminOut.model_validate(admin)
    out.permissions = perms
    return ApiResponse.ok(data=out)


@router.get("/dashboard", response_model=ApiResponse[dict])
async def dashboard_view(db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)):
    return ApiResponse.ok(data=await dashboard(db))


@router.get("/users", response_model=ApiResponse[dict])
async def users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    return ApiResponse.ok(data=await list_users(db, page=page, page_size=page_size))


@router.post("/users/{user_id}/ban", response_model=ApiResponse[dict])
async def ban(user_id: str, data: BanRequest, db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)):
    user = await ban_user(db, user_id, data.reason)
    return ApiResponse.ok(data={"id": str(user.id), "status": user.status})


@router.post("/users/{user_id}/unban", response_model=ApiResponse[dict])
async def unban(user_id: str, db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)):
    user = await unban_user(db, user_id)
    return ApiResponse.ok(data={"id": str(user.id), "status": user.status})


@router.get("/auth/email-config", response_model=ApiResponse[EmailRegisterConfig])
async def get_email_config(db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)):
    return ApiResponse.ok(data=await get_email_register_config(db))


@router.put("/auth/email-config", response_model=ApiResponse[EmailRegisterConfig])
async def put_email_config(
    data: EmailRegisterConfig, db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)
):
    payload = await update_email_register_config(db, data.model_dump())
    return ApiResponse.ok(data=EmailRegisterConfig(**payload))


@router.get("/reports", response_model=ApiResponse[dict])
async def reports(
    status: int = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
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
    _=Depends(get_current_admin),
):
    """List all items (any user's) with optional status filter and pagination."""
    data = await list_all_items(db, status=status if status is not None else None, page=page, page_size=page_size)
    return ApiResponse.ok(data=data)


# NOTE: 静态路径 /items/review-config 必须先于动态路径 /items/{item_id} 声明，
# 否则 "review-config" 会被当作 item_id 匹配。
@router.get("/items/review-config", response_model=ApiResponse[ItemReviewConfig])
async def admin_get_item_review(db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)):
    return ApiResponse.ok(data=ItemReviewConfig(**await get_item_review_config(db)))


@router.put("/items/review-config", response_model=ApiResponse[ItemReviewConfig])
async def admin_put_item_review(
    data: ItemReviewConfig, db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)
):
    payload = await update_item_review_config(db, data.model_dump())
    return ApiResponse.ok(data=ItemReviewConfig(**payload))


@router.patch("/items/{item_id}", response_model=ApiResponse[ItemOut])
async def admin_update_item_view(
    item_id: str,
    data: ItemUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Update any item's fields (e.g., take off sale). Bypasses owner check."""
    item = await admin_update_item(db, item_id, data)
    return ApiResponse.ok(data=ItemOut.model_validate(item))


@router.delete("/items/{item_id}", response_model=ApiResponse[None])
async def admin_delete_item_view(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Soft-delete any item. Bypasses owner check."""
    await admin_delete_item(db, item_id)
    return ApiResponse.ok(message="已删除")


@router.post("/items/{item_id}/approve", response_model=ApiResponse[ItemOut])
async def admin_approve_item_view(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """审核通过：待审核(PENDING) -> 上架(ON_SALE)。"""
    item = await approve_item(db, item_id)
    return ApiResponse.ok(data=ItemOut.model_validate(item))


@router.post("/items/{item_id}/reject", response_model=ApiResponse[ItemOut])
async def admin_reject_item_view(
    item_id: str,
    data: ItemReviewRejectRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """审核拒绝：待审核(PENDING) -> 下架(OFF_SHELF)。"""
    item = await reject_item(db, item_id, reason=data.reason)
    return ApiResponse.ok(data=ItemOut.model_validate(item))
