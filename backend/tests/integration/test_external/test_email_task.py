"""邮件任务集成测试：调用参数验证 + 已知缺口固化。

任务直接调用（不经 Celery broker）以验证参数与返回值；
真正的 broker 分发不在集成测试范围内。

已知缺口（P1，见 ``test_send_code_dispatches_email``）
----------------------------------------------------
``send_code`` 只生成并存储验证码，**没有派发任何邮件**；
``smtp_*`` 配置目前仅用于决定是否在响应里回传 ``debug_code``。
也就是说：一旦生产环境配置了 ``SMTP_HOST``，``debug_code`` 会停止回传，
而真实邮件又从未发出 —— 注册流程将彻底走不通。
修复方向：在 ``send_code`` 成功后 ``send_email.delay(to, subject, body)``。
"""

from __future__ import annotations

import pytest

import app.tasks.email as email_tasks

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# 任务本身
# ---------------------------------------------------------------------------
def test_send_email_task_returns_ok_with_recipient():
    """邮件任务按契约返回 ok 与收件人。"""
    result = email_tasks.send_email(
        to="student@example.edu.cn",
        subject="【校园生活平台】验证码",
        body="您的验证码是 123456",
    )
    assert result["ok"] is True
    assert result["to"] == "student@example.edu.cn"


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
# 与验证码流程的接线（当前缺失）
# ---------------------------------------------------------------------------
@pytest.mark.xfail(
    reason="功能缺口 P1：send_code 未派发邮件任务，"
    "生产配置 SMTP_HOST 后用户既收不到邮件、也拿不到 debug_code（见 docs/TESTING.md）",
    strict=False,
)
def test_send_code_dispatches_email(client, monkeypatch):
    """请求验证码**应当**触发一次邮件投递（当前实现未接线）。

    以 xfail 固化缺口：接入真实发信后本用例转为 XPASS，届时需移除标记。
    """
    dispatched = []

    def _fake_send_email(to, subject, body, html=None):
        dispatched.append({"to": to, "subject": subject, "body": body})
        return {"ok": True, "to": to}

    monkeypatch.setattr(email_tasks, "send_email", _fake_send_email)

    r = client.post(
        "/api/auth/send-code",
        json={"target": "emailtask@example.edu.cn", "purpose": "register"},
    )
    assert r.status_code == 200, r.text
    assert dispatched, "请求了验证码但没有派发任何邮件"
    assert dispatched[0]["to"] == "emailtask@example.edu.cn"
