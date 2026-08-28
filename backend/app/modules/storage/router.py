"""文件上传路由：/api/files/*。

- 客户端先请求 presign 拿到 object_key 与（MinIO）临时上传 URL
- 浏览器直传 MinIO；本地降级模式则通过 /api/files/upload 由后端落盘
- 仅允许图片上传（类型白名单 + 大小限制），拒绝其他文件类型
"""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import JSONResponse

from app.core.response import ApiResponse
from app.core.storage import storage_client
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
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB


def _image_ext_error(filename: str) -> JSONResponse:
    return JSONResponse(
        ApiResponse(code=40000, message="仅支持 JPG/PNG/WebP/GIF 图片上传", data=None).model_dump(),
        status_code=400,
    )


@router.post("/presign", response_model=ApiResponse[dict])
async def presign(
    prefix: str = Form(default="misc"),
    filename: str = Form(default="file.bin"),
    _: User = Depends(get_current_user),
):
    # MinIO 直传模式下内容无法在后端二次校验，这里先按扩展名白名单拦截
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in ALLOWED_IMAGE_EXTS:
        return _image_ext_error(filename)
    object_key = storage_client.gen_object_key(prefix, filename)
    upload_url = await storage_client.presigned_upload_url(object_key)
    return ApiResponse.ok(
        data={"object_key": object_key, "upload_url": upload_url, "direct": storage_client.enabled}
    )


@router.post("/upload", response_model=ApiResponse[dict])
async def upload(
    key: str = Form(...),
    file: UploadFile = File(...),
    _: User = Depends(get_current_user),
):
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
            ApiResponse(code=40000, message="图片大小不能超过 10MB", data=None).model_dump(),
            status_code=400,
        )
    await storage_client.upload_bytes(key, data, content_type=content_type)
    download_url = await storage_client.presigned_download_url(key)
    return ApiResponse.ok(data={"object_key": key, "url": download_url})


@router.get("/raw")
async def raw(key: str = Query(...)):
    """本地降级模式下载文件。"""
    if storage_client.enabled:
        from fastapi.responses import JSONResponse

        return JSONResponse(
            ApiResponse(code=40000, message="使用签名 URL 下载", data=None).model_dump(), status_code=400
        )
    local_path = os.path.join(storage_client.local_root, key.replace("/", "_"))
    if not os.path.isfile(local_path):
        from fastapi.responses import JSONResponse

        return JSONResponse(
            ApiResponse(code=40400, message="文件不存在", data=None).model_dump(), status_code=404
        )
    with open(local_path, "rb") as fh:
        content = fh.read()
    from fastapi.responses import Response

    return Response(content=content, media_type="application/octet-stream")
