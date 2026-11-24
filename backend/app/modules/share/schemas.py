"""资源共享 Pydantic 模型。"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ShareCreate(BaseModel):
    title: str = Field(min_length=1, max_length=128)
    description: str = Field(default="", max_length=2000)
    # file_key 只接受服务端签发的 uploads/{用户ID}/{32位hex}.{ext} 形态
    # （P1-2）：自由串可把任意 key（含他人对象）挂上资源并随列表公开暴露，
    # 私桶下载签名路径由此泄露他人文件。归属校验在 Service 层完成。
    file_key: str = ""
    category: str = "other"

    @field_validator("file_key")
    @classmethod
    def _key_must_be_server_issued(cls, v: str) -> str:
        if not v:
            return v
        from app.core.storage import OBJECT_KEY_RE

        if not OBJECT_KEY_RE.match(v):
            raise ValueError("file_key 必须为服务端签发的 uploads/{用户}/{uuid} 形式，请先调用上传接口")
        return v


class ShareOut(BaseModel):
    id: UUID
    owner_id: str
    title: str
    description: str
    file_key: str
    category: str
    downloads: int
    likes: int = 0
    download_url: str | None = None

    model_config = {"from_attributes": True}
