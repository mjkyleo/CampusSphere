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
        extra="allow",
        case_sensitive=False,
    )

    # ----- 应用基础 -----
    app_name: str = "campus-life-platform"
    debug: bool = False

    # ----- 数据库 -----
    db_url: str = "sqlite+aiosqlite:///./dev.db"

    # ----- Redis -----
    redis_url: str = "redis://localhost:6379/0"

    # ----- 安全 / JWT -----
    secret_key: str = "change-me-to-a-long-random-string-in-prod"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # ----- 限流 -----
    rate_limit_per_minute: int = 120

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
    ai: Dict[str, Any] = Field(default_factory=dict)

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
        for key in ("oauth", "minio", "meilisearch", "report_policy", "auth", "items", "ai"):
            if isinstance(data.get(key), dict):
                setattr(self, key, data[key])

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
