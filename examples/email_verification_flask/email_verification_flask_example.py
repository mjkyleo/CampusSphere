# -*- coding: utf-8 -*-
"""邮箱验证码集成示例（Flask 版）。

本示例与 CampusSphere 后端既有的「SMTP_SSL 发信 + 异步线程发送 + Redis 存储验证码」
风格保持一致，作为注册/登录流程中「邮箱验证码」能力的完整可运行参考实现。

覆盖内容：
  1. Flask 注册接口（路由 + 参数校验 + 调用异步发送 + 验证码写入 Redis(5 分钟过期) + JSON 响应）
  2. Redis 连接与存储验证码的工具函数（redis-py，含连接配置与 get/set 封装）
  3. 失败重试机制（装饰器：间隔 10 秒，最多 3 次）
  4. .env 文件示例 + python-dotenv 加载环境变量
  5. 发送频率控制（滑动窗口：每封间隔 ≥30 秒，每小时 ≤50 封）
  6. 备用邮箱切换逻辑（连续失败达阈值切换至 QQ 邮箱 SMTP 并告警管理员）

依赖（均为需求中明确点名的库，未引入其他框架）：
    pip install flask redis python-dotenv

运行步骤：
    cp .env.example .env          # 按需填写 SMTP / Redis / 管理员邮箱
    python email_verification_flask_example.py
    curl -X POST http://127.0.0.1:5000/api/auth/register \
         -H 'Content-Type: application/json' \
         -d '{"email":"user@school.edu.cn"}'
"""

from __future__ import annotations

import functools
import logging
import os
import re
import secrets
import smtplib
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from email.mime.text import MIMEText
from typing import Dict, Optional

import redis
from dotenv import load_dotenv
from flask import Flask, jsonify, request

# ---------------------------------------------------------------------------
# 4. 加载 .env 环境变量（python-dotenv）
#    必须在读取任何配置前调用；未提供 .env 时回退到下方默认值，保证示例可启动。
# ---------------------------------------------------------------------------
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("email_verify")


# ===========================================================================
# 2. Redis 连接与存储验证码工具函数（redis-py）
# ===========================================================================
@functools.lru_cache(maxsize=1)
def get_redis_client() -> redis.Redis:
    """返回进程级单例 Redis 客户端（连接池复用）。

    通过 from_url 创建，decode_responses=True 让取值直接为 str，避免 bytes 处理；
    socket_connect_timeout / socket_timeout 防止 Redis 不可用时请求长时间挂起。
    """
    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    return redis.Redis.from_url(
        url,
        encoding="utf-8",
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )


def redis_set(key: str, value: str, ttl: Optional[int] = None) -> None:
    """写入键值；ttl 为过期秒数（None 表示不过期）。"""
    get_redis_client().set(key, value, ex=ttl)


def redis_get(key: str) -> Optional[str]:
    """读取键值；不存在返回 None。"""
    return get_redis_client().get(key)


def redis_delete(key: str) -> None:
    """删除键。"""
    get_redis_client().delete(key)


def redis_incr(key: str, ttl: Optional[int] = None) -> int:
    """原子自增（用于失败计数 / 限速窗口），可选附带 TTL。"""
    client = get_redis_client()
    val = client.incr(key)
    if ttl:
        client.expire(key, ttl)
    return int(val)


# ===========================================================================
# 3. 失败重试机制（装饰器：间隔 10 秒，最多 3 次）
# ===========================================================================
def retry_on_failure(
    max_retries: int = 3,
    interval: float = 10.0,
    exceptions: tuple = (Exception,),
):
    """同步函数重试装饰器。

    被装饰函数抛出异常时，按 interval 秒间隔重试，最多 max_retries 次；
    全部失败后抛出最后一次异常。用于 SMTP 发送等可能瞬时失败的网络操作。
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc: Optional[BaseException] = None
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:  # noqa: BLE001
                    last_exc = exc
                    logger.warning(
                        "retry_attempt func=%s attempt=%s/%s error=%s",
                        func.__name__, attempt, max_retries, str(exc),
                    )
                    if attempt < max_retries:
                        time.sleep(interval)  # 间隔 10 秒
            assert last_exc is not None
            raise last_exc
        return wrapper
    return decorator


# ===========================================================================
# 5. 发送频率控制（滑动窗口：每封 ≥30 秒，每小时 ≤50 封）
# ===========================================================================
class RateLimitError(Exception):
    """发送频率超限。"""


class SendRateLimiter:
    """发送端全局限速器（针对 SMTP 账号，而非单个收件人）。

    - min_interval：相邻两封邮件最小间隔（秒），这里 30。
    - max_per_hour：每小时上限，这里 50。
    采用滑动窗口记录最近一小时内的发送时间戳，线程安全（本地锁）。
    注：多 Flask worker 部署时建议把状态改为 Redis 共享计数，示例保持单进程清晰。
    """
    def __init__(self, min_interval: int = 30, max_per_hour: int = 50):
        self.min_interval = min_interval
        self.max_per_hour = max_per_hour
        self._last_send_ts = 0.0
        self._hour_window: list[float] = []
        self._lock = threading.Lock()

    def acquire(self) -> None:
        """获取发送配额；不满足则抛出 RateLimitError。"""
        with self._lock:
            now = time.time()
            # 1) 相邻间隔控制：每封至少间隔 min_interval 秒
            if now - self._last_send_ts < self.min_interval:
                wait = self.min_interval - (now - self._last_send_ts)
                raise RateLimitError(f"发送过于频繁，请 {wait:.0f} 秒后再试")
            # 2) 每小时上限控制：清理一小时以前记录后判断是否超额
            self._hour_window = [t for t in self._hour_window if now - t < 3600]
            if len(self._hour_window) >= self.max_per_hour:
                raise RateLimitError("已达到每小时发送上限（50 封），请稍后重试")
            # 3) 配额通过，记录本次发送
            self._last_send_ts = now
            self._hour_window.append(now)


# ===========================================================================
# 6. 备用邮箱切换逻辑（连续失败达阈值 → 切换 QQ 邮箱 SMTP + 告警管理员）
# ===========================================================================
class SmtpFailover:
    """SMTP 主备切换。

    primary / backup 均为 dict（host/port/user/pass/from）。
    连续发送失败达到 threshold 次后切换到 backup，并通过 alert_admin 通知管理员；
    切换后若 backup 连续成功 recovery 次，则切回 primary（避免长期占用备用通道）。
    """
    def __init__(
        self,
        primary: Dict[str, str],
        backup: Dict[str, str],
        threshold: int = 3,
        recovery: int = 5,
        admin_email: Optional[str] = None,
    ):
        self.primary = primary
        self.backup = backup
        self.threshold = threshold
        self.recovery = recovery
        self.admin_email = admin_email
        self.using_backup = False
        self.consecutive_failures = 0
        self.consecutive_success = 0
        self._lock = threading.Lock()

    def current(self) -> Dict[str, str]:
        """返回当前应当使用的 SMTP 配置。"""
        return self.backup if self.using_backup else self.primary

    def report_success(self) -> None:
        with self._lock:
            self.consecutive_failures = 0
            if self.using_backup:
                self.consecutive_success += 1
                if self.consecutive_success >= self.recovery:
                    self.using_backup = False
                    self.consecutive_success = 0
                    logger.info("smtp_failback: switched back to primary")
                    self._alert(f"SMTP 已切回主邮箱（{self.primary['host']}）")

    def report_failure(self) -> None:
        with self._lock:
            self.consecutive_failures += 1
            self.consecutive_success = 0
            if not self.using_backup and self.consecutive_failures >= self.threshold:
                self.using_backup = True
                self.consecutive_failures = 0
                logger.warning("smtp_failover: switched to backup host=%s", self.backup["host"])
                self._alert(
                    f"主邮箱（{self.primary['host']}）连续 {self.threshold} 次发送失败，"
                    f"已切换至备用 QQ 邮箱（{self.backup['host']}），请检查主 SMTP 配置。"
                )

    def _alert(self, message: str) -> None:
        """向管理员发送告警（尽力而为，失败仅记录日志，不向上抛，避免递归）。"""
        if not self.admin_email:
            logger.warning("admin_alert_skipped: no ADMIN_ALERT_EMAIL configured")
            return
        try:
            # 告警邮件直连主邮箱发送，不经过限速器与故障切换，避免递归。
            _send_smtp(
                subject="【告警】校园平台邮件发送异常",
                to=self.admin_email,
                body=f"[CampusSphere] {message}\n时间：{time.strftime('%Y-%m-%d %H:%M:%S')}",
                cfg=self.primary,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("admin_alert_failed: %s", str(exc))


# ---------------------------------------------------------------------------
# SMTP 配置（从 .env 读取，缺失时给占位，便于本地直接 import 不报错）
# ---------------------------------------------------------------------------
PRIMARY_SMTP: Dict[str, str] = {
    "host": os.getenv("SMTP_HOST", "smtp.exmail.qq.com"),
    "port": int(os.getenv("SMTP_PORT", "465")),
    "user": os.getenv("SMTP_USER", "noreply@school.edu.cn"),
    "pass": os.getenv("SMTP_PASS", ""),
    "from": os.getenv("SMTP_FROM", "noreply@school.edu.cn"),
}
BACKUP_SMTP: Dict[str, str] = {
    "host": os.getenv("BACKUP_SMTP_HOST", "smtp.qq.com"),
    "port": int(os.getenv("BACKUP_SMTP_PORT", "465")),
    "user": os.getenv("BACKUP_SMTP_USER", "backup@qq.com"),
    "pass": os.getenv("BACKUP_SMTP_PASS", ""),
    "from": os.getenv("BACKUP_SMTP_FROM", "backup@qq.com"),
}
failover = SmtpFailover(
    primary=PRIMARY_SMTP,
    backup=BACKUP_SMTP,
    threshold=int(os.getenv("SMTP_FAILOVER_THRESHOLD", "3")),
    admin_email=os.getenv("ADMIN_ALERT_EMAIL"),
)
rate_limiter = SendRateLimiter(
    min_interval=int(os.getenv("SEND_MIN_INTERVAL", "30")),
    max_per_hour=int(os.getenv("SEND_MAX_PER_HOUR", "50")),
)


# ---------------------------------------------------------------------------
# 异步线程发送（与上文一致的「异步线程发送风格」）
# ---------------------------------------------------------------------------
# 后台线程池：邮件发送不阻塞 HTTP 请求返回。
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="mail")


# 业务调用方式不变：对外暴露 send_verification_code(email, code, purpose) 触发异步发送，
# 与 CampusSphere 既有的 send_code(target, purpose) 语义对齐（异步、非阻塞）。
def send_verification_code(email: str, code: str, purpose: str = "register") -> None:
    """提交验证码邮件到后台线程池，不阻塞当前请求。"""
    _executor.submit(_send_verification_email, email, code, purpose)


@retry_on_failure(max_retries=3, interval=10)
def _send_smtp(subject: str, to: str, body: str, cfg: Dict[str, str]) -> None:
    """通过 SMTP_SSL 发送单封邮件（带失败重试：间隔 10 秒，最多 3 次）。"""
    msg = MIMEText(body, _subtype="plain", _charset="utf-8")
    msg["Subject"] = subject
    msg["From"] = cfg["from"]
    msg["To"] = to
    # SMTP_SSL：端口 465，全程 TLS 加密，与上文发信方式保持一致。
    with smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=10) as server:
        server.login(cfg["user"], cfg["pass"])
        server.sendmail(cfg["from"], [to], msg.as_string())


def _send_verification_email(email: str, code: str, purpose: str) -> None:
    """后台线程执行的发送任务：限速 → 主备切换 → 发送（含重试） → 上报结果。"""
    try:
        rate_limiter.acquire()                              # 5. 频率控制
        cfg = failover.current()                            # 6. 取当前可用 SMTP
        _send_smtp(                                         # 3. 内部带 10s×3 重试
            subject="【校园生活平台】您的邮箱验证码",
            to=email,
            body=f"您的邮箱验证码为 {code}，5 分钟内有效。如非本人操作请忽略。",
            cfg=cfg,
        )
        failover.report_success()
        logger.info("verification_email_sent to=%s via=%s purpose=%s", email, cfg["host"], purpose)
    except RateLimitError as exc:
        # 频率超限不计入 SMTP 故障，直接记录，不触发主备切换。
        logger.warning("verification_email_rate_limited to=%s error=%s", email, str(exc))
    except Exception as exc:  # noqa: BLE001
        failover.report_failure()
        logger.error("verification_email_failed to=%s error=%s", email, str(exc))


# ===========================================================================
# 1. Flask 注册接口示例
# ===========================================================================
app = Flask(__name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
CODE_TTL_SECONDS = 300  # 验证码 5 分钟过期
CODE_COOLDOWN_SECONDS = 60  # 同一邮箱 60 秒内不重复发送，防刷


def generate_code(length: int = 6) -> str:
    """生成数字验证码（使用 secrets 保证不可预测）。"""
    return "".join(secrets.choice("0123456789") for _ in range(length))


@app.route("/api/auth/register", methods=["POST"])
def register():
    """注册接口：校验邮箱 → 生成验证码 → 写入 Redis(5 分钟过期) → 异步线程发信 → 返回 JSON。"""
    data = request.get_json(silent=True) or {}
    # 邮箱统一小写，避免大小写导致的 Redis key 不一致（与 CampusSphere 修复一致）。
    email = (data.get("email") or "").strip().lower()
    purpose = (data.get("purpose") or "register").strip()

    # —— 请求参数校验 ——
    if not email:
        return jsonify(code=400, msg="缺少邮箱参数"), 400
    if not EMAIL_RE.match(email):
        return jsonify(code=400, msg="邮箱格式不合法"), 400
    # 业务层防刷冷却（与限速器互补，针对单个收件人）
    if redis_get(f"vcode:cooldown:{purpose}:{email}"):
        return jsonify(code=429, msg="验证码发送过于频繁，请稍后重试"), 429

    # —— 生成验证码并写入 Redis（5 分钟过期）——
    code = generate_code()
    redis_set(f"vcode:{purpose}:{email}", code, ttl=CODE_TTL_SECONDS)
    # 60 秒冷却标记，防止短时间重复点击
    redis_set(f"vcode:cooldown:{purpose}:{email}", "1", ttl=CODE_COOLDOWN_SECONDS)

    # —— 调用异步发送函数（线程池，不阻塞请求）——
    send_verification_code(email, code, purpose=purpose)

    # —— 返回 JSON 响应 ——
    return jsonify(
        code=0,
        msg="验证码已发送，请查收邮箱",
        data={"email": email, "ttl": CODE_TTL_SECONDS},
    )


@app.route("/api/auth/register/verify", methods=["POST"])
def register_verify():
    """补充：校验验证码（注册第二步），展示 Redis 取值与一次性校验。"""
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    code = (data.get("code") or "").strip()
    purpose = (data.get("purpose") or "register").strip()

    if not email or not code:
        return jsonify(code=400, msg="缺少邮箱或验证码"), 400
    stored = redis_get(f"vcode:{purpose}:{email}")
    if not stored:
        return jsonify(code=400, msg="验证码已过期，请重新获取"), 400
    if stored != code:
        return jsonify(code=400, msg="验证码错误"), 400
    redis_delete(f"vcode:{purpose}:{email}")  # 一次性：校验成功即删除
    return jsonify(code=0, msg="验证通过")


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=os.getenv("FLASK_DEBUG", "false") == "true",
    )
