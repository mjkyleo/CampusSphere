"""一次性脚本：通过真实注册 API 创建 15 个测试用户（user01~user15 / 123456）。

用法：
    python scripts_seed_users.py

前置：后端服务须在 http://127.0.0.1:8000 运行。
脚本幂等：已存在的用户名会跳过；不逐个登录验证，避免触发认证端点限流（10/min）。
"""

from __future__ import annotations

import httpx

BASE = "http://127.0.0.1:8000"
PASSWORD = "123456"
USERS = [f"user{i:02d}" for i in range(1, 16)]


def main() -> None:
    created: list[str] = []
    skipped: list[str] = []
    failed: list[str] = []

    with httpx.Client(base_url=BASE, timeout=10.0) as client:
        for username in USERS:
            resp = client.post(
                "/api/auth/register",
                json={"username": username, "password": PASSWORD},
            )
            body = resp.json()
            code = body.get("code")
            if resp.status_code == 200 and code == 0:
                created.append(username)
            elif code == 40900 or "已存在" in str(body.get("message", "")):
                skipped.append(username)
            else:
                failed.append(f"{username}: {resp.status_code} {body}")

    print(f"created: {len(created)} -> {created}")
    print(f"skipped (exists): {len(skipped)} -> {skipped}")
    if failed:
        print(f"FAILED: {len(failed)}")
        for line in failed:
            print("  ", line)
    else:
        print("done. verify manually: user01 / 123456")


if __name__ == "__main__":
    main()
