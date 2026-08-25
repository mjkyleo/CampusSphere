"""文件上传路由：/api/files/*。

- 客户端先请求 presign 拿到 object_key 与（MinIO）临时上传 URL
- 浏览器直传 MinIO；本地降级模式则通过 /api/files/upload 由后端落盘
"""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import ApiResponse
from app.core.storage import storage_client
from app.modules.auth.deps import get_current_user
from app.modules.auth.models import User

router = APIRouter(prefix="/api/files", tags=["files"])


class PresignRequest:
    pass


@router.post("/presign", response_model=ApiResponse[dict])
async def presign(
    prefix: str = Form(default="misc"),
    filename: str = Form(default="file.bin"),
    _: User = Depends(get_current_user),
):
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
    await storage_client.upload_bytes(key, data, content_type=file.content_type or "application/octet-stream")
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
