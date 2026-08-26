"""对象存储（MinIO / S3 兼容）。

- 私有桶 + 临时签名 URL（上传/下载）
- 无 MinIO 时降级为本地磁盘存储（开发/测试零依赖）
- 懒连接：``StorageClient`` 在**导入时不连接网络**，首次实际调用时才尝试连接 MinIO，
  并设置 2s 连接超时，失败即回退本地存储，避免启动阻塞。
"""

from __future__ import annotations

import os
import uuid
from typing import Optional

import urllib3

from app.core.config import settings
from app.core.logging import get_logger

_logger = get_logger("core.storage")

try:
    from minio import Minio

    _MINIO_AVAILABLE = True
except Exception:  # noqa: BLE001
    Minio = None  # type: ignore
    _MINIO_AVAILABLE = False


class StorageClient:
    """统一对象存储客户端（懒连接）。"""

    def __init__(self) -> None:
        self._client = None
        # 是否已尝试过连接（保证只尝试一次）
        self._connected = False
        self.bucket = settings.minio_bucket
        self.local_root = os.path.join(os.getcwd(), "uploads")

    def _ensure_minio(self) -> None:
        """懒连接 MinIO（短超时）；失败回退本地。仅首次调用时执行。"""
        if self._connected:
            return
        self._connected = True
        if _MINIO_AVAILABLE and settings.minio_endpoint:
            try:
                # 短连接超时，避免无 MinIO 时长时间阻塞启动
                http_client = urllib3.PoolManager(
                    timeout=urllib3.Timeout(connect=2, read=5)
                )
                self._client = Minio(
                    settings.minio_endpoint,
                    access_key=settings.minio_access_key,
                    secret_key=settings.minio_secret_key,
                    secure=settings.minio_secure,
                    http_client=http_client,
                )
                if not self._client.bucket_exists(self.bucket):
                    self._client.make_bucket(self.bucket)
                _logger.info("minio_connected", bucket=self.bucket)
            except Exception as exc:  # noqa: BLE001
                _logger.warning("minio_unavailable_fallback_local", error=str(exc))
                self._client = None

    @property
    def enabled(self) -> bool:
        self._ensure_minio()
        return self._client is not None

    def _ensure_local(self) -> None:
        os.makedirs(self.local_root, exist_ok=True)

    @staticmethod
    def gen_object_key(prefix: str, filename: str) -> str:
        ext = os.path.splitext(filename)[1]
        return f"{prefix}/{uuid.uuid4().hex}{ext}"

    async def upload_bytes(
        self, object_key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        self._ensure_minio()
        if self._client is not None:
            from io import BytesIO

            self._client.put_object(
                self.bucket, object_key, BytesIO(data), length=len(data), content_type=content_type
            )
        else:
            self._ensure_local()
            with open(os.path.join(self.local_root, object_key.replace("/", "_")), "wb") as fh:
                fh.write(data)
        return object_key

    async def presigned_upload_url(self, object_key: str, expires: int = 600) -> str:
        self._ensure_minio()
        if self._client is not None:
            return self._client.presigned_put_object(self.bucket, object_key, expires=expires)
        # 本地降级：返回内部上传地址
        return f"/api/files/upload?key={object_key}"

    async def presigned_download_url(self, object_key: str, expires: int = 600) -> str:
        self._ensure_minio()
        if self._client is not None:
            return self._client.presigned_get_object(self.bucket, object_key, expires=expires)
        return f"/api/files/raw?key={object_key}"

    def list_keys(self) -> list[dict]:
        """枚举存储中的全部对象，返回 ``[{key, size}]``。

        本地降级模式下文件名约定为 ``object_key.replace("/", "_")``
        （即 ``prefix_uuid.ext``），这里按第一个 ``_`` 还原 object_key。
        """
        self._ensure_minio()
        if self._client is not None:
            out = []
            for obj in self._client.list_objects(self.bucket, recursive=True):
                out.append({"key": obj.object_name, "size": int(obj.size or 0)})
            return out
        self._ensure_local()
        out = []
        for fn in sorted(os.listdir(self.local_root)):
            path = os.path.join(self.local_root, fn)
            if not os.path.isfile(path) or "_" not in fn:
                continue
            prefix, rest = fn.split("_", 1)
            out.append({"key": f"{prefix}/{rest}", "size": os.path.getsize(path)})
        return out

    def remove_key(self, object_key: str) -> None:
        """删除指定对象；对象不存在时静默成功（幂等）。"""
        self._ensure_minio()
        if self._client is not None:
            self._client.remove_object(self.bucket, object_key)
            return
        self._ensure_local()
        path = os.path.join(self.local_root, object_key.replace("/", "_"))
        if os.path.isfile(path):
            os.remove(path)


# 全局单例（导入即创建，但不在导入时连接网络）
storage_client = StorageClient()
