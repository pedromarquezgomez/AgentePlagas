from dataclasses import dataclass, field
from typing import Any

from app.schemas.incoming_message import IncomingMessage
from app.skills.contracts import ProductSkill
from app.tools.contracts import BackendTool


@dataclass(frozen=True)
class ConversationContext:
    message: IncomingMessage
    channel: str
    user_id: str
    conversation_id: str
    incident_id: str | None = None
    incident_summary: str | None = None
    history: list[dict[str, Any]] = field(default_factory=list)
    available_skills: list[ProductSkill] = field(default_factory=list)
    available_tools: list[BackendTool] = field(default_factory=list)
    policy_constraints: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
