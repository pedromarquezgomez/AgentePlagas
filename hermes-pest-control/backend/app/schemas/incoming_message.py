from typing import Any

from pydantic import BaseModel, Field

from app.schemas.types import Channel, MessageType


class IncomingMessage(BaseModel):
    channel: Channel
    external_user_id: str
    external_chat_id: str
    message_type: MessageType
    text: str | None = None
    attachments: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
