"""消息模块 Pydantic 模型。"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class MessageOut(BaseModel):
    id: UUID
    conversation_id: str
    sender_id: str
    type: int
    content: str
    is_read: bool
    created_at: str = ""

    model_config = {"from_attributes": True}


class ParticipantOut(BaseModel):
    user_id: str
    last_read_at: str | None = None

    model_config = {"from_attributes": True}


class ConversationOut(BaseModel):
    id: UUID
    conv_type: str
    related_id: str | None = None
    participants: list[ParticipantOut] = []
    last_message: MessageOut | None = None
    unread_count: int = 0
    target_user: dict | None = None

    model_config = {"from_attributes": True}


class SendMessageRequest(BaseModel):
    type: int = 0
    content: str


class ReadRequest(BaseModel):
    last_read_message_id: str | None = None
