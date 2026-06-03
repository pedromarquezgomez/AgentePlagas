from dataclasses import dataclass, field
from typing import Any

from app.schemas.incoming_message import IncomingMessage
from app.skills.contracts import ProductSkill


@dataclass(frozen=True)
class AgentRuntimeRequest:
    incoming_message: IncomingMessage
    conversation_history: list[dict[str, Any]] = field(default_factory=list)
    business_context: dict[str, Any] = field(default_factory=dict)
    available_skills: list[ProductSkill] = field(default_factory=list)
