# -*- coding: utf-8 -*-
"""端到端验证新认证流程：email-config -> send-code(debug) -> email-register(即登录) -> me -> login"""
import json
import sys
import time
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8000"
PROXY = "http://127.0.0.1:5173"

def req(url, method="GET", body=None, token=None):
    r = urllib.request.Request(url, method=method)
    r.add_header("Content-Type", "application/json")
    if token:
        r.add_header("Authorization", f"Bearer {token}")
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(r, data=data, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {"code": -1, "message": e.reason}
    except Exception as e:
        return 0, {"code": -1, "message": str(e)}

def wait_ready(url, tries=40):
    for _ in range(tries):
        s, _ = req(url)
        if s == 200:
            return True
        time.sleep(1)
    return False

def main():
    if not wait_ready(BASE + "/health"):
        print("[FAIL] backend not ready"); sys.exit(1)
    if not wait_ready(PROXY + "/", tries=60):
        print("[FAIL] frontend not ready"); sys.exit(1)
    print("[OK] backend + frontend ready")

    # 1. 公开邮箱注册规则
    s, r = req(PROXY + "/api/auth/email-config")
    print(f"[1] email-config  status={s} code={r.get('code')} data={r.get('data')}")
    assert s == 200 and r.get("code") == 0, "email-config failed"

    # 2. 发送验证码（测试模式应返回 debug_code）
    s, r = req(PROXY + "/api/auth/send-code", "POST", {"target": "test_user@example.edu.cn", "purpose": "register"})
    print(f"[2] send-code    status={s} code={r.get('code')} debug_code={r.get('data', {}).get('debug_code')}")
    assert s == 200 and r.get("code") == 0, "send-code failed"
    debug_code = r.get("data", {}).get("debug_code")
    assert debug_code, "debug_code missing in dev mode"

    # 3. 邮箱注册（注册即登录，应返回 token）
    s, r = req(PROXY + "/api/auth/email-register", "POST",
               {"email": "test_user@example.edu.cn", "password": "Test@123456", "code": debug_code, "nickname": "测试同学"})
    print(f"[3] email-register status={s} code={r.get('code')} has_token={bool((r.get('data') or {}).get('access_token'))}")
    assert s == 200 and r.get("code") == 0 and r.get("data", {}).get("access_token"), "email-register token missing"
    token = r["data"]["access_token"]

    # 4. 用新 token 拉取个人信息
    s, r = req(PROXY + "/api/users/me", token=token)
    me = r.get("data") or {}
    print(f"[4] users/me     status={s} code={r.get('code')} username={me.get('username')} email={me.get('email')}")
    assert s == 200 and r.get("code") == 0 and me.get("email") == "test_user@example.edu.cn", "getMe failed"

    # 5. 密码登录
    s, r = req(PROXY + "/api/auth/login", "POST", {"account": "test_user@example.edu.cn", "password": "Test@123456"})
    print(f"[5] login        status={s} code={r.get('code')} has_token={bool((r.get('data') or {}).get('access_token'))}")
    assert s == 200 and r.get("code") == 0, "login failed"

    # 6. 管理员登录
    s, r = req(PROXY + "/api/admin/login", "POST", {"username": "admin", "password": "admin123"})
    print(f"[6] admin-login  status={s} code={r.get('code')} has_token={bool((r.get('data') or {}).get('access_token'))}")
    assert s == 200 and r.get("code") == 0, "admin login failed"
    admin_token = r["data"]["access_token"]
    s, r = req(PROXY + "/api/admin/me", token=admin_token)
    print(f"[7] admin/me     status={s} code={r.get('code')} username={(r.get('data') or {}).get('username')}")
    assert s == 200 and r.get("code") == 0, "admin me failed"

    print("\nALL CHECKS PASSED")

if __name__ == "__main__":
    main()
