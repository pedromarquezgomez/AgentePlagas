from pydantic import BaseModel

from app.schemas.types import Channel


class Conversation(BaseModel):
    id: str
    channel: Channel
    external_user_id: str
    external_chat_id: str
    status: str
