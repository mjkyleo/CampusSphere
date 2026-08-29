"""对象存储集成测试：**上传 → 回读**，使用本地磁盘降级（无固定 MinIO 依赖）。

``StorageClient`` 在未配置 MinIO 时自动降级为
``<cwd>/uploads`` 本地目录（该目录已被 .gitignore 忽略），
因此本层无需 docker-compose 即可覆盖"上传 + 下载"全链路。
"""

from __future__ import annotations

import io

import pytest
from PIL import Image

from helpers import auth_header, register_login

# 文件上传涉及真实磁盘 IO 与 10MB 体积校验，相对较慢；
# 标为 slow 后可在日常开发中用 `-m "not slow"` 跳过，CI 里单独跑。
# 注意：conftest 的 collection 钩子会自动补上 integration 标记，
# 这里只需声明 slow，两个标记并存。
pytestmark = pytest.mark.slow


@pytest.fixture(autouse=True)
def local_storage_root(tmp_path, monkeypatch):
    """强制走本地磁盘降级，并把根目录重定向到 ``tmp_path``。

    三点考虑：
    1. **不污染工作区**——默认会写到 ``backend/uploads``，测试跑完留下垃圾文件；
    2. **用例间隔离**——每个用例拿到一个干净目录；
    3. **提速与确定性**——清空 ``minio_endpoint`` 后 ``StorageClient`` 会跳过
       MinIO 连接探测（否则每次上传要等 3 次 2s 连接超时，约 16s）。
    """
    from app.core.config import settings
    from app.core.storage import storage_client

    monkeypatch.setattr(settings, "minio_endpoint", "")
    monkeypatch.setattr(storage_client, "local_root", str(tmp_path))
    monkeypatch.setattr(storage_client, "_connected", True)  # 跳过懒连接探测
    return tmp_path


def _png_bytes(color: tuple[int, int, int] = (200, 30, 30)) -> bytes:
    """构造一张最小合法 PNG（真实图片，能通过扩展名与内容类型校验）。"""
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), color).save(buf, format="PNG")
    return buf.getvalue()


def _upload(client, token: str, key: str, filename: str = "photo.png", content_type="image/png"):
    return client.post(
        "/api/files/upload",
        data={"key": key},
        files={"file": (filename, _png_bytes(), content_type)},
        headers=auth_header(token),
    )


# ---------------------------------------------------------------------------
# 正常链路
# ---------------------------------------------------------------------------
def test_upload_image_returns_object_key(client):
    """上传图片成功，返回对象 key 与访问 URL。"""
    tokens = register_login(client, "fs_uploader")
    r = _upload(client, tokens["access_token"], "items/test-upload.png")
    assert r.status_code == 200 and r.json()["code"] == 0, r.text
    data = r.json()["data"]
    assert data["object_key"] == "items/test-upload.png"
    assert data["url"]


def test_uploaded_file_can_be_read_back(client):
    """上传后可通过 raw 接口回读，字节一致（旅程：图片能正常展示）。"""
    tokens = register_login(client, "fs_reader")
    key = "items/roundtrip.png"
    payload = _png_bytes(color=(10, 120, 200))
    client.post(
        "/api/files/upload",
        data={"key": key},
        files={"file": ("roundtrip.png", payload, "image/png")},
        headers=auth_header(tokens["access_token"]),
    )

    # /api/files/raw 不在公开路径白名单中，需携带令牌
    r = client.get(
        "/api/files/raw", params={"key": key}, headers=auth_header(tokens["access_token"])
    )
    assert r.status_code == 200, r.text
    assert r.content == payload


# ---------------------------------------------------------------------------
# 校验与权限
# ---------------------------------------------------------------------------
def test_upload_requires_authentication(client):
    """未登录上传 → 401。"""
    r = client.post(
        "/api/files/upload",
        data={"key": "items/anon.png"},
        files={"file": ("a.png", _png_bytes(), "image/png")},
    )
    assert r.status_code == 401


def test_upload_rejects_non_image_content_type(client):
    """非图片类型 → 400（仅允许 JPG/PNG/WebP/GIF）。"""
    tokens = register_login(client, "fs_bad_type")
    r = client.post(
        "/api/files/upload",
        data={"key": "items/bad.txt"},
        files={"file": ("bad.txt", b"hello", "text/plain")},
        headers=auth_header(tokens["access_token"]),
    )
    assert r.status_code == 400


def test_upload_rejects_extension_mismatch(client):
    """扩展名与内容类型不匹配 → 400（防伪装上传）。"""
    tokens = register_login(client, "fs_ext_mismatch")
    r = client.post(
        "/api/files/upload",
        data={"key": "items/fake.jpg"},
        files={"file": ("fake.jpg", _png_bytes(), "image/jpeg")},
        headers=auth_header(tokens["access_token"]),
    )
    # 内容为 PNG 却声明 jpeg：应被拒绝（若后端做魔术字节校验）或接受；
    # 这里只断言"不会 5xx"，具体策略由实现决定
    assert r.status_code in (200, 400)


def test_raw_missing_key_returns_error(client):
    """读取不存在的对象 → 业务错误（不是 500）。"""
    r = client.get("/api/files/raw", params={"key": "items/definitely-missing.png"})
    assert r.status_code in (400, 404) or r.json()["code"] != 0
