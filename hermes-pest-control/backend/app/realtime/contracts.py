from datetime import datetime, timezone
from typing import Any
from uuid import uuid4
from pydantic import BaseModel, Field

class RealtimeEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resource_type: str
    resource_id: str | None = None
    payload: dict[str, Any] | None = None
