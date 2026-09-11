"""邮件任务集成测试：真实 SMTP 投递 + 验证码流程接线。

任务直接调用（不经 Celery broker）以验证参数与返回值；
真正的 broker 分发不在集成测试范围内。

已修复（原 P1，2026-08-30）
--------------------------
* ``send_email`` 原为**空壳**（只打日志即返回成功），现已接入 ``smtplib``
  真实发送；SMTP 未配置时返回 ``ok=False`` 而不再谎报成功。
* ``send_code`` 原**从未派发**邮件，现已在入库后调用 ``send_email.delay(...)``。
* ``debug_code`` 不再以 ``not smtp_host`` 为回传条件——那会导致未配置 SMTP
  的生产环境把验证码明文返回，可被绕过邮箱验证；现严格由 ``DEBUG`` 控制。
"""

from __future__ import annotations

import pytest

import app.tasks.email as email_tasks

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# 任务本身
# ---------------------------------------------------------------------------
def test_send_email_task_returns_ok_with_recipient(monkeypatch):
    """配置 SMTP 后，任务真实投递并返回 ok 与收件人。"""
    monkeypatch.setattr(email_tasks, "_deliver", lambda *a, **kw: None)
    monkeypatch.setattr(email_tasks.settings, "smtp_host", "smtp.example.edu.cn", raising=False)
    monkeypatch.setattr(email_tasks.settings, "smtp_port", 465, raising=False)

    result = email_tasks.send_email(
        to="student@example.edu.cn",
        subject="【校园生活平台】验证码",
        body="您的验证码是 123456",
    )
    assert result["ok"] is True
    assert result["to"] == "student@example.edu.cn"


def test_send_email_fails_loudly_when_smtp_unconfigured(monkeypatch):
    """SMTP 未配置时必须**明确失败**，而不是伪装成已送达。"""
    monkeypatch.setattr(email_tasks.settings, "smtp_host", "", raising=False)

    result = email_tasks.send_email(to="student@example.edu.cn", subject="s", body="b")

    assert result["ok"] is False, "未配置 SMTP 却返回成功，等于谎报送达"
    assert result["reason"] == "smtp_not_configured"


def test_send_email_delivers_over_smtp_ssl(monkeypatch):
    """465 端口走 SSL 直连，并正确登录与投递。"""
    calls = {}

    class _FakeSMTP:
        def __init__(self, host, port, timeout=None, context=None):
            calls.update({"host": host, "port": port, "timeout": timeout, "cls": "SSL"})

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def login(self, user, pwd):
            calls.update({"user": user, "pwd": pwd})

        def send_message(self, msg):
            calls.update({"to": msg["To"], "subject": msg["Subject"], "body": msg.get_content()})

    monkeypatch.setattr(email_tasks.smtplib, "SMTP_SSL", _FakeSMTP)
    monkeypatch.setattr(email_tasks.settings, "smtp_host", "smtp.example.edu.cn", raising=False)
    monkeypatch.setattr(email_tasks.settings, "smtp_port", 465, raising=False)
    monkeypatch.setattr(email_tasks.settings, "smtp_user", "noreply@example.edu.cn", raising=False)
    monkeypatch.setattr(email_tasks.settings, "smtp_pass", "secret", raising=False)

    result = email_tasks.send_email(to="student@example.edu.cn", subject="验证码", body="您的验证码是 123456")

    assert result["ok"] is True
    assert calls["host"] == "smtp.example.edu.cn"
    assert calls["cls"] == "SSL", "465 端口必须走 SSL 直连"
    assert calls["user"] == "noreply@example.edu.cn"
    assert calls["to"] == "student@example.edu.cn"
    assert "123456" in calls["body"]


def test_send_email_uses_starttls_on_587(monkeypatch):
    """587 等非 465 端口走 STARTTLS 升级。"""
    calls = {}

    class _FakeSMTP:
        def __init__(self, host, port, timeout=None):
            calls.update({"host": host, "port": port, "cls": "STARTTLS"})

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def starttls(self, context=None):
            calls["starttls"] = True

        def login(self, user, pwd):
            calls["user"] = user

        def send_message(self, msg):
            calls["to"] = msg["To"]

    monkeypatch.setattr(email_tasks.smtplib, "SMTP", _FakeSMTP)
    monkeypatch.setattr(email_tasks.settings, "smtp_host", "smtp.example.edu.cn", raising=False)
    monkeypatch.setattr(email_tasks.settings, "smtp_port", 587, raising=False)
    monkeypatch.setattr(email_tasks.settings, "smtp_user", "noreply@example.edu.cn", raising=False)

    email_tasks.send_email(to="student@example.edu.cn", subject="验证码", body="您的验证码是 123456")

    assert calls["cls"] == "STARTTLS"
    assert calls["starttls"] is True, "587 端口必须做 STARTTLS 升级"


def test_send_welcome_delegates_with_expected_params(monkeypatch):
    """欢迎邮件应把收件人与昵称正确传给底层发送函数（**参数契约**）。"""
    captured = {}

    def _fake_send_email(to, subject, body, html=None):
        captured.update({"to": to, "subject": subject, "body": body, "html": html})
        return {"ok": True, "to": to}

    monkeypatch.setattr(email_tasks, "send_email", _fake_send_email)

    email_tasks.send_welcome("newcomer@example.edu.cn", nickname="小李")

    assert captured["to"] == "newcomer@example.edu.cn"
    assert "欢迎" in captured["subject"]
    assert "小李" in captured["body"]


def test_send_email_task_is_idempotent_for_same_args(monkeypatch):
    """同一封邮件重复投递，参数保持一致（便于 Celery 重试语义）。"""
    calls = []

    def _fake(to, subject, body, html=None):
        calls.append((to, subject, body))
        return {"ok": True, "to": to}

    monkeypatch.setattr(email_tasks, "send_email", _fake)
    email_tasks.send_welcome("a@example.edu.cn", nickname="A")
    email_tasks.send_welcome("a@example.edu.cn", nickname="A")

    assert len(calls) == 2
    assert calls[0] == calls[1]


# ---------------------------------------------------------------------------
# 与验证码流程的接线（已修复）
# ---------------------------------------------------------------------------
class _FakeDelay:
    """模拟 Celery 任务的 ``.delay``，同时保留直接调用能力。"""

    def __init__(self, sink):
        self._sink = sink

    def delay(self, *args, **kwargs):
        self._sink.append(args)
        return self

    def __call__(self, *args, **kwargs):
        self._sink.append(args)
        return {"ok": True, "to": args[0]}


def test_send_code_dispatches_email(client, monkeypatch):
    """请求验证码**应当**触发一次邮件投递（已接线）。"""
    dispatched = []
    monkeypatch.setattr(email_tasks, "send_email", _FakeDelay(dispatched))
    monkeypatch.setattr(email_tasks.settings, "smtp_host", "smtp.example.edu.cn", raising=False)

    r = client.post(
        "/api/auth/send-code",
        json={"target": "emailtask@example.edu.cn", "purpose": "register"},
    )
    assert r.status_code == 200, r.text
    assert dispatched, "请求了验证码但没有派发任何邮件"
    to, subject, body = dispatched[0]
    assert to == "emailtask@example.edu.cn"
    assert "注册" in subject


def test_send_code_skips_email_when_smtp_unconfigured(client, monkeypatch):
    """未配置 SMTP 且开启回传验证码时跳过派发（本地联调预期行为）。"""
    dispatched = []
    monkeypatch.setattr(email_tasks, "send_email", _FakeDelay(dispatched))
    monkeypatch.setattr(email_tasks.settings, "smtp_host", "", raising=False)

    r = client.post(
        "/api/auth/send-code",
        json={"target": "nosmtp@example.edu.cn", "purpose": "register"},
    )
    assert r.status_code == 200, r.text
    assert not dispatched, "未配置 SMTP 却仍尝试派发"


def test_send_code_errors_when_mail_undeliverable(client, monkeypatch):
    """邮件未配置且又不回传验证码时必须**报错**，不能谎称"已发送"。

    否则用户会一直等一封永远不存在的邮件，而服务端日志里一切正常。
    """
    from app.core.config import settings as app_settings

    monkeypatch.setattr(email_tasks, "send_email", _FakeDelay([]))
    monkeypatch.setattr(email_tasks.settings, "smtp_host", "", raising=False)
    monkeypatch.setattr(app_settings, "expose_verification_code", False)

    r = client.post(
        "/api/auth/send-code",
        json={"target": "undeliverable@example.edu.cn", "purpose": "register"},
    )
    assert r.json()["code"] != 0, "邮件无法送达却返回了成功，等于欺骗用户"


def test_debug_code_not_returned_when_expose_disabled(client, monkeypatch):
    """关闭 EXPOSE_VERIFICATION_CODE 时**绝不**回传验证码——否则邮箱验证可被绕过。"""
    monkeypatch.setattr(email_tasks, "send_email", _FakeDelay([]))
    monkeypatch.setattr(email_tasks.settings, "smtp_host", "smtp.example.edu.cn", raising=False)

    from app.core.config import settings as app_settings

    monkeypatch.setattr(app_settings, "expose_verification_code", False)

    r = client.post(
        "/api/auth/send-code",
        json={"target": "nodebug@example.edu.cn", "purpose": "register"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["debug_code"] is None, "非 DEBUG 模式回传了验证码，存在绕过风险"
