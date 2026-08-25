"""冒烟测试：健康检查与网关鉴权中间件。"""

from __future__ import annotations


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


def test_protected_requires_token(client):
    r = client.get("/api/users/me")
    assert r.status_code == 401


def test_protected_bad_token_rejected(client):
    r = client.get("/api/users/me", headers={"Authorization": "Bearer not.a.valid.jwt"})
    assert r.status_code == 401
