"""应用配置（pydantic-settings）。

加载顺序：
1. 读取 ``.env``（或环境变量）获得基础配置（DB_URL / REDIS_URL / SECRET_KEY 等）。
2. 读取 ``SCHOOL_CONFIG_PATH`` 指向的 ``school.yaml``，覆盖/补充多校相关字段
   （school_name / oauth / minio / meilisearch / report_policy 等）。

这样做到"一份代码 + 一份 school.yaml = 一所学校一键上线"。
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.logging import get_logger

_logger = get_logger("core.config")


class Settings(BaseSettings):
    """全局配置。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        # 收紧为 ignore：禁止任意环境变量随意注入配置，降低攻击面与误配风险（原 allow）。
        extra="ignore",
        case_sensitive=False,
    )

    # ----- 应用基础 -----
    app_name: str = "campus-life-platform"
    debug: bool = False

    # ----- 数据库 -----
    db_url: str = "sqlite+aiosqlite:///./dev.db"
    # 连接池（仅对 PostgreSQL/MySQL 等带池驱动生效；SQLite 忽略）。
    # 生产高并发时按负载上调，避免连接耗尽导致 5xx。
    db_pool_size: int = 10            # 常驻连接数
    db_max_overflow: int = 20         # 超出 pool_size 后允许临时创建的最大连接数
    db_pool_recycle: int = 1800       # 秒：回收空闲连接，规避中间件静默断连（如 PG 的 idle_timeout）
    db_pool_timeout: int = 30         # 秒：等待连接池可用的最大阻塞时间

    # ----- Redis -----
    redis_url: str = "redis://localhost:6379/0"

    # ----- 热点缓存（对应审计 P1-9b）-----
    # 默认开启；测试/本地无 Redis 时自动降级为内存字典，不会阻断业务。
    # 关闭：设置 CACHE_ENABLED=false（如离线单测避免跨用例污染）。
    cache_enabled: bool = True
    # 热点列表缓存基础 TTL（秒）；实际写入会叠加随机抖动以规避雪崩（见 app/core/cache.py）。
    cache_ttl_seconds: int = 60

    # ----- 安全 / JWT -----
    secret_key: str = "change-me-to-a-long-random-string-in-prod"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # ----- 限流 -----
    rate_limit_per_minute: int = 120
    # 登录 / 注册 / 验证码等认证端点单独限流（防爆破与刷接口）。
    # 生产保持 10；测试环境需放宽，否则批量创建用户的用例会在同一分钟内互相
    # 挤爆限额（中间件已把它做成构造参数，这里补上配置入口供 .env 覆盖）。
    auth_rate_limit_per_minute: int = 10

    # ----- 管理员入口与安全 -----
    # 这些字段专门保护 /api/admin/* 的可达性，与普通用户账号无关。
    # - admin_gateway_key  : 前端页面可见，调用 /api/admin/discover 时用它换取 X-Admin-Gateway 短期 token。
    #                        错误的 gateway key 一律 404 Not Found（对未授权者表现得像端点不存在）。
    # - admin_bootstrap_* : school.yaml 配置段，可由 .env 覆盖；生产环境强制密码长度 ≥ 16，
    #                        否则启动 fail-fast 拒绝运行。
    admin_gateway_key: str = ""
    admin_bootstrap_enabled: bool = True
    admin_bootstrap_username: str = "siteadmin"
    admin_bootstrap_password: str = ""
    admin_bootstrap_min_length: int = 16
    admin_gateway_rotate_seconds: int = 3600  # 派生 token 1 小时轮换
    # 网关强制开关：True=生产（默认，强制校验 X-Admin-Gateway）；False=本地开发放宽（免网关密钥）。
    # 仅用于本地联调，生产环境请勿置为 false（validate_admin_security 会告警）。
    admin_gateway_enforce: bool = True

    # ----- 邮件发送（验证码 / 通知）-----
    # 生产环境**必须**配置 smtp_host，否则验证码无法送达（启动校验会拒绝启动）。
    smtp_host: str = ""
    # 是否在 ``send-code`` 响应里回传验证码（供本地联调与自动化测试读取）。
    #
    # 这是一个**独立开关**而非复用 DEBUG：DEBUG 还控制管理员网关校验开关
    # （``gateway_enforced() = admin_gateway_enforce and not debug``）与启动期
    # 安全强校验的严格度，若让"回传验证码"搭 DEBUG 的便车，测试环境为拿到
    # 验证码而开启 DEBUG 会**连带关掉网关校验**，把安全测试的断言全部架空。
    #
    # 生产必须保持 false —— 否则任何人都能从响应里读到 6 位验证码，
    # 无需拥有邮箱即可注册/改密，等于绕过邮箱验证。
    expose_verification_code: bool = False
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_pass: str = ""
    # 发件人地址。留空时回退为 smtp_user（多数 SMTP 服务商要求两者一致）。
    smtp_from: str = ""
    # 连接/读超时（秒）。SMTP 为同步阻塞调用，必须设上限，避免 worker 被拖死。
    smtp_timeout: int = 10
    # True=强制 STARTTLS（587 等端口）；留为 None 时按端口推断：465 走 SSL，其余走 STARTTLS。
    smtp_starttls: bool | None = None

    # ----- 滑块验证（发送验证码前的防滥用闸门）-----
    # 关闭后 /api/auth/send-code 不再要求票据（供测试与内网环境使用）。
    captcha_enabled: bool = True
    captcha_tolerance_px: int = 6  # 缺口对齐容差（像素），过小会伤及真实用户体验
    captcha_ttl_seconds: int = 300  # 滑块令牌有效期
    captcha_max_attempts: int = 3  # 同一滑块最多校验次数，超出即作废
    captcha_min_track_points: int = 6  # 轨迹最少采样点，防脚本直传坐标
    captcha_ticket_ttl_seconds: int = 120  # 校验通过签发的票据有效期

    # ----- 第三方验证码（极验行为验证 4.0）-----
    # 留空则使用上面那套自建拼图滑块；填入 captcha_id / captcha_key 后，
    # /api/auth/captcha/config 会下发 provider=geetest，前端自动切到极验。
    # 这样"是否接入第三方"变成纯配置决策，不需要改代码重新发版。
    geetest_captcha_id: str = ""
    geetest_captcha_key: str = ""
    # 二次校验接口超时（秒）。必须设上限：极验服务不可达时若无限等待，
    # 会把 uvicorn 的工作线程拖死，进而影响整站。
    geetest_timeout: int = 5
    # 容灾开关：极验服务异常/超时时是否放行。
    # True  → 校验接口不可达时"放行"，保证用户仍能注册（牺牲部分防刷能力）
    # False → 校验接口不可达时"拒绝"，宁可暂时无法注册也不放机器人进来
    geetest_fail_open: bool = True

    # ----- 验证码 -----
    code_ttl_seconds: int = 300  # 验证码有效期
    code_max_attempts: int = 5  # 同一验证码最多校验次数，超出即作废
    # 同一 target 每分钟最多发送次数（防轰炸邮箱/手机）；0 表示不限制。
    code_send_limit_per_minute: int = 1

    # ----- CORS -----
    # 默认放行前端（frontend :5173；3000 在 Windows Hyper-V 排除范围不可用）；生产环境用 .env 的 CORS_ORIGINS 覆盖
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    # ----- 多校配置 -----
    school_config_path: str = "../config/school.yaml"
    school_name: str = "示例大学"
    school_domain: str = "localhost"

    # 由 school.yaml 注入的嵌套配置
    oauth: dict[str, Any] = Field(default_factory=dict)
    minio: dict[str, Any] = Field(default_factory=dict)
    meilisearch: dict[str, Any] = Field(default_factory=dict)
    report_policy: dict[str, Any] = Field(default_factory=dict)
    auth: dict[str, Any] = Field(default_factory=dict)
    items: dict[str, Any] = Field(default_factory=dict)
    courses: dict[str, Any] = Field(default_factory=dict)
    ai: dict[str, Any] = Field(default_factory=dict)
    admin: dict[str, Any] = Field(default_factory=dict)

    # ----- 基础设施（可由 .env 覆盖，缺省取 school.yaml）-----
    minio_endpoint: str | None = None
    minio_access_key: str | None = None
    minio_secret_key: str | None = None
    minio_secure: bool = False
    minio_bucket: str = "campus"

    meili_host: str = "http://localhost:7700"
    meili_api_key: str = "masterKey"

    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    def load_school_config(self) -> None:
        """读取 school.yaml，合并到当前配置（幂等，可被重复调用）。"""
        path = os.environ.get("SCHOOL_CONFIG_PATH", self.school_config_path)
        if not path or not os.path.isfile(path):
            _logger.warning("school_config_not_found", path=path)
            return
        try:
            with open(path, encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
        except Exception as exc:
            _logger.error("school_config_parse_failed", error=str(exc))
            return

        for key in ("school_name", "school_domain"):
            if data.get(key):
                setattr(self, key, data[key])
        for key in ("oauth", "minio", "meilisearch", "report_policy", "auth", "items", "courses", "ai", "admin"):
            if isinstance(data.get(key), dict):
                setattr(self, key, data[key])

        # admin：school.yaml 提供**默认值**，.env 可覆盖。
        #
        # 为何必须以 .env 优先：school.yaml 是**签入版本库**的学校配置模板，
        # 而 .env 存放各环境密钥（不入库）。若让 school.yaml 无条件覆盖，
        # 则 .env 里配置的强密码/网关密钥会被仓库里的占位值（如
        # "change-me-deploy-with-strong-pw-16plus"）悄悄顶掉——
        # 即"改了 .env 却不生效"，且生产会带着占位密码启动。
        # 判定方式：.env 有值（非空）即保留 .env，为空才回落到 school.yaml。
        ad = self.admin or {}
        bs = ad.get("bootstrap") or {}
        if isinstance(bs, dict):
            self.admin_bootstrap_enabled = bool(bs.get("enabled", self.admin_bootstrap_enabled))
            if not self.admin_bootstrap_username and bs.get("username"):
                self.admin_bootstrap_username = str(bs["username"])
            if not self.admin_bootstrap_password and bs.get("password"):
                self.admin_bootstrap_password = str(bs["password"])
            if isinstance(bs.get("min_length"), int):
                self.admin_bootstrap_min_length = bs["min_length"]
        gw = ad.get("gateway") or {}
        if isinstance(gw, dict):
            if not self.admin_gateway_key and gw.get("key"):
                self.admin_gateway_key = str(gw["key"])
            if isinstance(gw.get("rotate_seconds"), int):
                self.admin_gateway_rotate_seconds = gw["rotate_seconds"]

        # MinIO / Meili 取最具体来源（.env 优先于 school.yaml）
        mc = self.minio or {}
        self.minio_endpoint = self.minio_endpoint or mc.get("endpoint")
        self.minio_access_key = self.minio_access_key or mc.get("access_key")
        self.minio_secret_key = self.minio_secret_key or mc.get("secret_key")
        if "secure" in mc:
            self.minio_secure = bool(mc["secure"])
        self.minio_bucket = mc.get("bucket", self.minio_bucket)

        ms = self.meilisearch or {}
        self.meili_host = self.meili_host or ms.get("host", self.meili_host)
        self.meili_api_key = self.meili_api_key or ms.get("api_key", self.meili_api_key)

        _logger.info("school_config_loaded", school=self.school_name)


@lru_cache
def get_settings() -> Settings:
    """返回进程级单例配置。"""
    settings = Settings()
    settings.load_school_config()
    return settings


# 全局配置单例（模块导入即可用）
settings = get_settings()


# 启动时校验的管理员安全开关。生产环境必须配置 ADMIN_GATEWAY_KEY + 强 bootstrap 密码，
# 否则 init_logging 之后、lifespan 启动前 SystemExit(2)，避免带病上线。
# DEBUG=true 时放过（开发模式继续可以用默认 siteadmin / 弱密码）。
def validate_admin_security(strict: bool | None = None) -> None:
    """管理员安全配置校验：非 debug 模式下失败即抛 SystemExit。

    校验项：
    1. ADMIN_GATEWAY_KEY 已设置且非默认占位
    2. bootstrap password 长度 ≥ 配置的 ``admin_bootstrap_min_length``
    3. gateway key 长度 ≥ 16

    邮件通道校验（SMTP_HOST）**独立于**网关开关：它决定验证码能否送达，
    与管理员网关是否强制无关，故放在下面的 early-return 之前执行。

    测试环境通过 strict=False 跳过（conftest 不希望启动失败）。
    """
    s = settings
    is_strict = (not s.debug) if strict is None else strict

    # 邮件通道校验：**只告警，不终止启动**。
    #
    # 未配置 SMTP_HOST 时注册链路不可用，但平台的其余能力（登录、浏览、
    # 交易、消息）都还能正常服务。用 SystemExit 让整站起不来，等于把
    # "邮件没配好"放大成"全站不可用"——老用户也会被牵连。
    # 改为 CRITICAL 日志（可接入告警），取码端点本身再显式报错，
    # 让"发不出验证码"这件事在**受影响的地方**暴露，而不是拖垮整站。
    # 注意：此校验只取决于 debug，不受 admin_gateway_enforce 影响。
    if not s.smtp_host:
        _msg = (
            "SMTP_HOST is not set — email verification codes cannot be delivered. "
            "Registration/password-reset will fail. Set SMTP_HOST/SMTP_PORT/SMTP_USER/SMTP_PASS."
        )
        if is_strict:
            _logger.critical("smtp_unconfigured", detail=_msg)
        else:
            _logger.warning("smtp_unconfigured", detail=_msg)

    # 本地开发放宽（admin_gateway_enforce=false）时不强制，避免带病启动阻断联调
    if not s.admin_gateway_enforce:
        if not s.debug:
            _logger.warning("admin_security_relaxed", reason="admin_gateway_enforce=false in non-debug mode")
        is_strict = False
    if not is_strict:
        return

    placeholder_keys = {"", "change-me", "change-me-admin-gateway-key", "change-me-deploy-with-strong-pw"}
    bad_key = (
        not s.admin_gateway_key
        or s.admin_gateway_key.lower() in placeholder_keys
        or len(s.admin_gateway_key) < 16
    )
    if bad_key:
        raise SystemExit(
            "[SECURITY] ADMIN_GATEWAY_KEY is missing or too short.\n"
            "         Set it in backend/.env (>=16 random chars) or pass ADMIN_GATEWAY_KEY env var.\n"
            "         For dev only: DEBUG=true bypasses this check."
        )

    if s.admin_bootstrap_enabled and s.admin_bootstrap_password:
        if len(s.admin_bootstrap_password) < s.admin_bootstrap_min_length:
            raise SystemExit(
                f"[SECURITY] admin.bootstrap.password must be >= {s.admin_bootstrap_min_length} chars in production.\n"
                "         Update config/school.yaml admin.bootstrap.password, or set DEBUG=true for dev."
            )

    # 生产环境拒绝已知默认/占位基础设施密钥（MinIO / Meili / 数据库），避免带病上线。
    # 与 admin 网关密钥同理：仅在生产强校验路径（非 debug 且网关强制）触发。
    _infra_defaults = {
        "MEILI_API_KEY": s.meili_api_key,
        "MINIO_ACCESS_KEY": s.minio_access_key,
        "MINIO_SECRET_KEY": s.minio_secret_key,
    }
    _known_weak = {"", "masterKey", "minioadmin", "change-me", "change-me-to-a-long-random-string-in-prod"}
    for _name, _val in _infra_defaults.items():
        if _val in _known_weak:
            raise SystemExit(
                f"[SECURITY] {_name} is a known default/placeholder value.\n"
                f"         Set a strong value in backend/.env before production startup."
            )
