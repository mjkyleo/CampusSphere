"""文件上传路由：/api/files/*。

- 客户端先请求 presign 拿到 object_key 与直传策略（MinIO 为带 policy 的
  POST form；本地降级则通过 /api/files/upload 由后端落盘）
- 对象键一律由**服务端**生成并绑定上传者：``uploads/{user_id}/{uuid}{ext}``，
  客户端传入的 prefix 不参与命名空间（P1-2 信任链）
- 仅允许图片上传（类型白名单 + 大小限制），拒绝其他文件类型
"""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import JSONResponse, Response
from starlette.concurrency import run_in_threadpool

from app.core.response import ApiResponse
from app.core.storage import (
    MAX_UPLOAD_SIZE,
    ensure_user_object_key,
    gen_user_object_key,
    storage_client,
)
from app.modules.auth.deps import get_current_user
from app.modules.auth.models import User

router = APIRouter(prefix="/api/files", tags=["files"])

# 图片类型白名单：MIME -> 允许的扩展名集合
ALLOWED_IMAGE_TYPES: dict[str, set[str]] = {
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
    "image/webp": {".webp"},
    "image/gif": {".gif"},
}
ALLOWED_IMAGE_EXTS: set[str] = {ext for exts in ALLOWED_IMAGE_TYPES.values() for ext in exts}
MAX_IMAGE_SIZE = MAX_UPLOAD_SIZE  # 10MB


def _image_ext_error(filename: str) -> JSONResponse:
    return JSONResponse(
        ApiResponse(code=40000, message="仅支持 JPG/PNG/WebP/GIF 图片上传", data=None).model_dump(),
        status_code=400,
    )


@router.post("/presign", response_model=ApiResponse[dict])
async def presign(
    prefix: str = Form(default="misc"),
    filename: str = Form(default="file.bin"),
    user: User = Depends(get_current_user),
):
    # MinIO 直传模式下内容无法在后端二次校验，这里先按扩展名白名单拦截
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in ALLOWED_IMAGE_EXTS:
        return _image_ext_error(filename)
    # 对象键由服务端生成并绑定上传者；prefix 仅作兼容保留，不参与命名空间，
    # 否则客户端可指定任意前缀预签名，覆盖同名已知对象。
    object_key = gen_user_object_key(str(user.id), filename)
    if storage_client.enabled:
        post = await storage_client.presigned_upload_post(object_key)
        return ApiResponse.ok(
            data={
                "object_key": object_key,
                "upload_url": post["url"],
                "fields": post["fields"],
                "direct": True,
            }
        )
    return ApiResponse.ok(
        data={
            "object_key": object_key,
            "upload_url": f"/api/files/upload?key={object_key}",
            "fields": {},
            "direct": False,
        }
    )


@router.post("/upload", response_model=ApiResponse[dict])
async def upload(
    key: str = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    # 信任链（P1-2）：key 必须是服务端签发给**当前用户**的命名空间键，
    # 否则任何登录用户可用任意 key 覆盖他人对象（头像/物品图片——uuid
    # 不可猜但也不是秘密）。形态与归属统一在 ensure_user_object_key 校验。
    try:
        ensure_user_object_key(key, str(user.id))
    except ValueError:
        return JSONResponse(
            ApiResponse(code=40000, message="非法的文件标识", data=None).model_dump(),
            status_code=400,
        )
    data = await file.read()
    content_type = (file.content_type or "").lower()
    allowed_exts = ALLOWED_IMAGE_TYPES.get(content_type)
    if allowed_exts is None:
        return JSONResponse(
            ApiResponse(code=40000, message="仅支持 JPG/PNG/WebP/GIF 图片上传", data=None).model_dump(),
            status_code=400,
        )
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed_exts:
        return _image_ext_error(file.filename or "")
    if len(data) > MAX_IMAGE_SIZE:
        return JSONResponse(
            ApiResponse(code=40000, message="图片大小不能超过 10MB", data=None).model_dump(), status_code=400
        )
    try:
        await storage_client.upload_bytes(key, data, content_type=content_type)
    except ValueError:
        # key 非法（穿越/越界/超长）：local_path_for 校验失败
        return JSONResponse(
            ApiResponse(code=40000, message="非法的文件标识", data=None).model_dump(), status_code=400
        )
    download_url = await storage_client.presigned_download_url(key)
    return ApiResponse.ok(data={"object_key": key, "url": download_url})


@router.get("/raw")
async def raw(key: str = Query(...)):
    """本地降级模式下载文件。

    信任模型与签名 URL 一致：object_key 内含 128 位随机 uuid，充当能力
    凭证，故不做登录校验（前端 ``<img src>`` 场景也无法携带 Header）。
    但 key 必须能映射回 uploads 根目录之内的路径 —— 路径折叠与越界校验
    统一走 :meth:`StorageClient.local_path_for`（历史版本在此存在 Windows
    反斜杠穿越，可读任意文件）。
    """
    if storage_client.enabled:
        return JSONResponse(
            ApiResponse(code=40000, message="使用签名 URL 下载", data=None).model_dump(), status_code=400
        )
    try:
        local_path = storage_client.local_path_for(key)
    except ValueError:
        return JSONResponse(
            ApiResponse(code=40000, message="非法的文件标识", data=None).model_dump(), status_code=400
        )
    # 同步文件 IO 会阻塞事件循环，投入线程池执行
    if not await run_in_threadpool(local_path.is_file):
        return JSONResponse(
            ApiResponse(code=40400, message="文件不存在", data=None).model_dump(), status_code=404
        )
    content = await run_in_threadpool(local_path.read_bytes)
    return Response(content=content, media_type="application/octet-stream")
