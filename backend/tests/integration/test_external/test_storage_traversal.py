"""本地降级存储的路径穿越防护测试。

历史缺陷：``/api/files/raw`` 与 ``/api/files/upload`` 对客户端可控的
``key`` 只做了 ``replace("/", "_")`` —— Windows 下反斜杠仍是路径分隔符，
``..\\..\\`` 可穿越出 uploads 目录读/写任意文件；``Path`` 拼接绝对路径
（如 ``C:\\x``）还会整体替换基准目录。

修复后统一走 ``StorageClient.local_path_for``：分隔符/盘符折叠为下划线 +
resolve 后越界校验。核心不变量（本文件全部断言围绕它展开）：

    **无论 key 是什么，读到的/写出的文件永远位于 local_root 之内。**
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from helpers import auth_header, register_login, user_key
from PIL import Image


@pytest.fixture(autouse=True)
def local_storage_root(tmp_path, monkeypatch):
    """与 test_storage_upload.py 相同的隔离手法：本地降级 + 重定向根目录。"""
    from app.core.config import settings
    from app.core.storage import storage_client

    monkeypatch.setattr(settings, "minio_endpoint", "")
    monkeypatch.setattr(storage_client, "local_root", str(tmp_path))
    monkeypatch.setattr(storage_client, "_connected", True)
    return tmp_path


def _png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (8, 8)).save(buf, format="PNG")
    return buf.getvalue()


class TestLocalPathFor:
    """local_path_for 的纯单元层校验。"""

    def test_windows_backslash_traversal_is_contained(self, tmp_path):
        from app.core.storage import storage_client

        storage_client.local_root = str(tmp_path)
        p = storage_client.local_path_for("..\\..\\..\\windows\\win.ini")
        assert p.is_relative_to(Path(tmp_path).resolve())

    def test_absolute_path_is_contained(self, tmp_path):
        from app.core.storage import storage_client

        storage_client.local_root = str(tmp_path)
        p = storage_client.local_path_for("C:\\Windows\\system32\\config")
        assert p.is_relative_to(Path(tmp_path).resolve())

    def test_normal_key_round_trips(self, tmp_path):
        from app.core.storage import storage_client

        storage_client.local_root = str(tmp_path)
        p = storage_client.local_path_for("item/abc123.png")
        assert p.is_relative_to(Path(tmp_path).resolve())
        assert p.name == "item_abc123.png"

    @pytest.mark.parametrize("bad", ["", "..", "x" * 600])
    def test_invalid_keys_rejected(self, tmp_path, bad):
        from app.core.storage import storage_client

        storage_client.local_root = str(tmp_path)
        with pytest.raises(ValueError):
            storage_client.local_path_for(bad)


class TestRawEndpointTraversal:
    """/api/files/raw 对穿越 key 的响应必须不泄露根目录外的任何文件。"""

    _EVIL_KEYS = [
        "..\\..\\..\\secret.txt",
        "..%2F..%2Fsecret.txt",  # 请求层解码后为 ../..//secret.txt
        "C:\\Windows\\win.ini",
        "..",
    ]

    def test_raw_never_serves_outside_file(self, client, tmp_path):
        user = register_login(client, "travuser")

        # 在根目录**外**放一个诱饵文件，穿越成功的话就能读到它
        decoy = tmp_path.parent / "decoy_secret.txt"
        decoy.write_text("TOP-SECRET-OUTSIDE", encoding="utf-8")
        try:
            for evil in self._EVIL_KEYS:
                resp = client.get("/api/files/raw", params={"key": evil})
                assert resp.status_code != 200, f"穿越 key 未被拦截: {evil}"
                assert "TOP-SECRET-OUTSIDE" not in resp.text
        finally:
            decoy.unlink(missing_ok=True)

    def test_raw_serves_legitimate_object(self, client):
        user = register_login(client, "travuser")
        key = user_key(user["user_id"], ".png")
        r = client.post(
            "/api/files/upload",
            data={"key": key},
            files={"file": ("ok.png", _png_bytes(), "image/png")},
            headers=auth_header(user["access_token"]),
        )
        assert r.status_code == 200, r.text
        # 网关中间件要求非公开路径携带 token；该端点实际仅供本地联调/测试回读
        resp = client.get(
            "/api/files/raw",
            params={"key": key},
            headers=auth_header(user["access_token"]),
        )
        assert resp.status_code == 200
        assert resp.content[:8] == _png_bytes()[:8]


class TestUploadEndpointTraversal:
    """上传 key 穿越时：要么 400，要么安全折叠落盘在根目录内。"""

    def test_upload_never_writes_outside_root(self, client, tmp_path):
        user = register_login(client, "travuser")
        decoy_dir = tmp_path.parent
        r = client.post(
            "/api/files/upload",
            data={"key": "..\\evil.png"},
            files={"file": ("evil.png", _png_bytes(), "image/png")},
            headers=auth_header(user["access_token"]),
        )
        # 400（拒绝）或 200（折叠为根目录内安全文件名）皆可，但绝不允许
        # 在根目录之外产生文件
        if r.status_code == 200:
            written = list(Path(tmp_path).rglob("*"))
            assert all(Path(tmp_path).resolve() in p.resolve().parents or p.parent == Path(tmp_path) for p in written if p.is_file())
        assert not (decoy_dir / "evil.png").exists()
