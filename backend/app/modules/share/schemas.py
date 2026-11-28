"""资源共享 Pydantic 模型。"""

from __future__ import annotations

from datetime import datetime
from urllib.parse import urlparse
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


def _check_external_url(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("资源链接必须是完整的 http(s) 地址")
    return value


class ShareCreate(BaseModel):
    title: str = Field(min_length=1, max_length=128)
    description: str = Field(default="", max_length=2000)
    # file_key 只接受服务端签发的 uploads/{用户ID}/{32位hex}.{ext} 形态
    # （P1-2）：自由串可把任意 key（含他人对象）挂上资源并随列表公开暴露，
    # 私桶下载签名路径由此泄露他人文件。归属校验在 Service 层完成。
    file_key: str = ""
    # 多数资料由用户自行提供网盘 / 课程站 / 开源仓库链接，平台不托管文件。
    file_url: str = ""
    category: str = "other"
    tags: list[str] = Field(default_factory=list, max_length=8)

    @field_validator("file_key")
    @classmethod
    def _key_must_be_server_issued(cls, v: str) -> str:
        if not v:
            return v
        from app.core.storage import OBJECT_KEY_RE

        if not OBJECT_KEY_RE.match(v):
            raise ValueError("file_key 必须为服务端签发的 uploads/{用户}/{uuid} 形式，请先调用上传接口")
        return v

    @field_validator("file_url")
    @classmethod
    def _url_must_be_http(cls, v: str) -> str:
        return _check_external_url(v)

    @field_validator("tags")
    @classmethod
    def _clean_tags(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        for raw in values or []:
            tag = str(raw).strip().lstrip("#")
            if tag and len(tag) <= 20 and tag not in cleaned:
                cleaned.append(tag)
        return cleaned[:8]

    @model_validator(mode="after")
    def _require_one_link(self) -> "ShareCreate":
        if not self.file_url and not self.file_key:
            raise ValueError("请提供资源链接，或先上传附件")
        return self


class ShareOut(BaseModel):
    id: UUID
    owner_id: str
    owner_nickname: str = ""
    title: str
    description: str
    file_key: str = ""
    file_url: str = ""
    category: str
    downloads: int
    likes: int = 0
    tags: list[str] = Field(default_factory=list)
    download_url: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
