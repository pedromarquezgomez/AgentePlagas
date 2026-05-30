from typing import Any

from pydantic import BaseModel, Field

from app.schemas.types import Channel


class OutgoingMessage(BaseModel):
    channel: Channel
    external_chat_id: str
    text: str
    attachments: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
