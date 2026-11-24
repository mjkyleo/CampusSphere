"""对象存储（MinIO / S3 兼容）。

- 私有桶 + 临时签名 URL（上传/下载）
- 无 MinIO 时降级为本地磁盘存储（开发/测试零依赖）
- 懒连接：``StorageClient`` 在**导入时不连接网络**，首次实际调用时才尝试连接 MinIO，
  并设置 2s 连接超时，失败即回退本地存储，避免启动阻塞。
"""

from __future__ import annotations

import os
import re
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import urllib3
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.logging import get_logger

_logger = get_logger("core.storage")

try:
    from minio import Minio

    _MINIO_AVAILABLE = True
except Exception:
    Minio = None  # type: ignore
    _MINIO_AVAILABLE = False

# 服务端签发的对象键形态（P1-2 信任链）：
#   uploads/{用户UUID}/{32位hex}.{1-8位字母数字扩展名}
# 上传入口（presign）只签发该形态的 key，入库入口（ItemImageIn/ShareCreate）
# 只接受该形态的 key —— 客户端无法把任意字符串（他人对象、URL、穿越路径）
# 挂到自己的业务记录上。
OBJECT_KEY_RE = re.compile(r"^uploads/[0-9a-fA-F-]{36}/[0-9a-f]{32}(?:\.[A-Za-z0-9]{1,8})?$")

# 直传体积上限：与 /api/files/upload 的 MAX_IMAGE_SIZE 保持一致（10MB）
MAX_UPLOAD_SIZE = 10 * 1024 * 1024


def gen_user_object_key(user_id: str, filename: str) -> str:
    """生成绑定上传者的对象键：``uploads/{user_id}/{uuid}{ext}``。

    前缀由服务端决定（客户端传什么 prefix 都不影响命名空间），
    uuid 文件名不可枚举；键与上传者绑定后，业务入库校验才能确认
    "图片确实是他自己传的"。
    """
    ext = os.path.splitext(filename or "")[1].lower()
    return f"uploads/{user_id}/{uuid.uuid4().hex}{ext}"


def ensure_user_object_key(key: str, user_id: str) -> None:
    """校验 key 为服务端签发给该用户的对象键（P1-2 信任链闭环）。

    :raises ValueError: 形态不符（非 uploads/{uuid}/{32hex}.ext）或不属于该用户。
    """
    if not key or not OBJECT_KEY_RE.match(key):
        raise ValueError("object key must be a server-issued uploads/{user}/{uuid} key")
    if not key.startswith(f"uploads/{user_id}/"):
        raise ValueError("object key does not belong to this user")


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
            except Exception as exc:
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
        """旧版键生成：``{prefix}/{uuid}{ext}``。

        .. deprecated:: P1-2
            prefix 客户端可控导致命名空间不可信，新代码一律用
            :func:`gen_user_object_key`（服务端绑定上传者）。保留仅为兼容。
        """
        ext = os.path.splitext(filename)[1]
        return f"{prefix}/{uuid.uuid4().hex}{ext}"

    def local_path_for(self, object_key: str) -> Path:
        """object_key → 本地降级模式的落盘路径（穿越安全）。

        上传（``upload_bytes``）与下载（``/api/files/raw``）必须共用本映射：
        任意一方单独放宽都会造成读写的不是同一个路径。分隔符（``/``、``\\``）
        与 ``:``（Windows 盘符 / NTFS 数据流）一律折叠为下划线，最终
        ``resolve()`` 后校验必须仍位于 local_root 之内 —— 此前只替换了 ``/``，
        Windows 下 ``..\\..\\`` 与绝对路径（``Path`` 拼接绝对路径会整体替换
        基准目录）都能逃出 uploads 目录，构成任意文件读写。

        :raises ValueError: key 为空、超长或折叠后仍越界（调用方应转为 4xx）。
        """
        if not object_key or len(object_key) > 512:
            raise ValueError("invalid object key")
        root = Path(self.local_root).resolve()
        name = (
            object_key.replace("\\", "_").replace("/", "_").replace(":", "_")
        )
        candidate = (root / name).resolve()
        if not candidate.is_relative_to(root):
            raise ValueError("object key escapes local root")
        return candidate

    async def upload_bytes(
        self, object_key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        self._ensure_minio()
        if self._client is not None:
            from io import BytesIO

            # 同步 MinIO 客户端会阻塞 asyncio 事件循环，投入线程池执行。
            await run_in_threadpool(
                self._client.put_object,
                self.bucket,
                object_key,
                BytesIO(data),
                length=len(data),
                content_type=content_type,
            )
        else:
            self._ensure_local()
            # 同步文件写会阻塞事件循环，与上面 MinIO 分支一致投入线程池
            local_path = await run_in_threadpool(self.local_path_for, object_key)
            await run_in_threadpool(local_path.write_bytes, data)
        return object_key

    async def presigned_upload_url(self, object_key: str, expires: int = 600) -> str:
        self._ensure_minio()
        if self._client is not None:
            # 同步客户端调用投入线程池，避免阻塞事件循环。
            return await run_in_threadpool(
                self._client.presigned_put_object, self.bucket, object_key, expires=expires
            )
        # 本地降级：返回内部上传地址
        return f"/api/files/upload?key={object_key}"

    async def presigned_upload_post(
        self,
        object_key: str,
        expires_seconds: int = 600,
        max_size: int = MAX_UPLOAD_SIZE,
    ) -> dict:
        """带策略的预签名直传（POST form），返回 ``{"url", "fields"}``。

        相比 presigned_put_object（裸 PUT，服务端无法约束内容），POST policy
        把约束**写进签名**，MinIO 服务端会拒绝越界请求：

        * ``key`` 精确等于签发键 —— 客户端改 key 即签名失效，无法覆盖他人对象
        * ``content-length-range`` 限制体积（防超大对象撑爆配额）
        * ``content-type`` 必须以 image/ 开头（与扩展名白名单双保险）

        本地降级模式无签名机制，返回内部上传端点（该端点自行校验 key 归属
        与内容），``fields`` 为空。
        """
        self._ensure_minio()
        if self._client is not None:
            from minio.datatypes import PostPolicy

            def _build() -> dict:
                policy = PostPolicy(
                    self.bucket, datetime.now(UTC) + timedelta(seconds=expires_seconds)
                )
                policy.add_equals_condition("key", object_key)
                policy.add_content_length_range_condition(1, max_size)
                policy.add_starts_with_condition("Content-Type", "image/")
                form = self._client.presigned_post_policy(policy)
                # key 的取值本身也是必须回传的表单字段（policy 只含约束条件）
                form["key"] = object_key
                return form

            fields = await run_in_threadpool(_build)
            scheme = "https" if settings.minio_secure else "http"
            return {"url": f"{scheme}://{settings.minio_endpoint}/{self.bucket}", "fields": fields}
        return {"url": "/api/files/upload", "fields": {}}

    async def presigned_download_url(self, object_key: str, expires: int = 600) -> str:
        self._ensure_minio()
        if self._client is not None:
            return await run_in_threadpool(
                self._client.presigned_get_object, self.bucket, object_key, expires=expires
            )
        return f"/api/files/raw?key={object_key}"

    async def warmup(self) -> None:
        """预热 MinIO 连接（lifespan 启动期调用，线程池执行不阻塞事件循环）。

        ``_ensure_minio`` 首次调用会做同步网络 IO（``bucket_exists``）；
        若不在启动期预热，冷启动后的**第一个**上传/签名请求会在事件循环上
        承担这次阻塞。未配置 MinIO 时本方法为空操作。
        """
        await run_in_threadpool(self._ensure_minio)

    async def list_keys(self) -> list[dict]:
        """枚举存储中的全部对象，返回 ``[{key, size}]``。

        本地降级模式下文件名约定为 ``object_key.replace("/", "_")``
        （即 ``prefix_uuid.ext``），这里按第一个 ``_`` 还原 object_key。
        同步 MinIO/文件 IO 投入线程池，避免阻塞事件循环。
        """
        self._ensure_minio()
        if self._client is not None:
            def _list_remote() -> list[dict]:
                return [
                    {"key": obj.object_name, "size": int(obj.size or 0)}
                    for obj in self._client.list_objects(self.bucket, recursive=True)
                ]

            return await run_in_threadpool(_list_remote)
        self._ensure_local()

        def _list_local() -> list[dict]:
            out: list[dict] = []
            for fn in sorted(os.listdir(self.local_root)):
                path = os.path.join(self.local_root, fn)
                if not os.path.isfile(path) or "_" not in fn:
                    continue
                prefix, rest = fn.split("_", 1)
                out.append({"key": f"{prefix}/{rest}", "size": os.path.getsize(path)})
            return out

        return await run_in_threadpool(_list_local)

    async def remove_key(self, object_key: str) -> None:
        """删除指定对象；对象不存在时静默成功（幂等）。同步 IO 投入线程池。"""
        self._ensure_minio()
        if self._client is not None:
            await run_in_threadpool(
                self._client.remove_object, self.bucket, object_key
            )
            return
        self._ensure_local()
        path = self.local_path_for(object_key)
        if path.is_file():
            await run_in_threadpool(path.unlink)

# 全局单例（导入即创建，但不在导入时连接网络）
storage_client = StorageClient()
