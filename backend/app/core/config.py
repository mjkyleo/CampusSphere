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
from typing import Any, Dict, List, Optional

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
    # 未配置 SMTP 时，验证码接口会返回 debug_code 便于测试联调；
    # 配置后验证码仅通过邮件送达，生产环境必须配置。
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_pass: str = ""

    # ----- CORS -----
    # 默认放行前端（frontend :5173；3000 在 Windows Hyper-V 排除范围不可用）；生产环境用 .env 的 CORS_ORIGINS 覆盖
    cors_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    # ----- 多校配置 -----
    school_config_path: str = "../config/school.yaml"
    school_name: str = "示例大学"
    school_domain: str = "localhost"

    # 由 school.yaml 注入的嵌套配置
    oauth: Dict[str, Any] = Field(default_factory=dict)
    minio: Dict[str, Any] = Field(default_factory=dict)
    meilisearch: Dict[str, Any] = Field(default_factory=dict)
    report_policy: Dict[str, Any] = Field(default_factory=dict)
    auth: Dict[str, Any] = Field(default_factory=dict)
    items: Dict[str, Any] = Field(default_factory=dict)
    courses: Dict[str, Any] = Field(default_factory=dict)
    ai: Dict[str, Any] = Field(default_factory=dict)
    admin: Dict[str, Any] = Field(default_factory=dict)

    # ----- 基础设施（可由 .env 覆盖，缺省取 school.yaml）-----
    minio_endpoint: Optional[str] = None
    minio_access_key: Optional[str] = None
    minio_secret_key: Optional[str] = None
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
            with open(path, "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
        except Exception as exc:  # noqa: BLE001
            _logger.error("school_config_parse_failed", error=str(exc))
            return

        for key in ("school_name", "school_domain"):
            if data.get(key):
                setattr(self, key, data[key])
        for key in ("oauth", "minio", "meilisearch", "report_policy", "auth", "items", "courses", "ai", "admin"):
            if isinstance(data.get(key), dict):
                setattr(self, key, data[key])

        # admin：school.yaml 的 admin.bootstrap.{enabled,username,password,min_length} 可由 .env 覆盖
        ad = self.admin or {}
        bs = ad.get("bootstrap") or {}
        if isinstance(bs, dict):
            self.admin_bootstrap_enabled = bool(bs.get("enabled", self.admin_bootstrap_enabled))
            if bs.get("username"):
                self.admin_bootstrap_username = str(bs["username"])
            if bs.get("password"):
                self.admin_bootstrap_password = str(bs["password"])
            if isinstance(bs.get("min_length"), int):
                self.admin_bootstrap_min_length = bs["min_length"]
        gw = ad.get("gateway") or {}
        if isinstance(gw, dict):
            if gw.get("key"):
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
def validate_admin_security(strict: Optional[bool] = None) -> None:
    """管理员安全配置校验：非 debug 模式下失败即抛 SystemExit。

    校验项：
    1. ADMIN_GATEWAY_KEY 已设置且非默认占位
    2. bootstrap password 长度 ≥ 配置的 ``admin_bootstrap_min_length``
    3. gateway key 长度 ≥ 16

    测试环境通过 strict=False 跳过（conftest 不希望启动失败）。
    """
    s = settings
    is_strict = (not s.debug) if strict is None else strict
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
