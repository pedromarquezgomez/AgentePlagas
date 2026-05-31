from typing import Any

from pydantic import BaseModel, Field

from app.schemas.types import AgentActionType, IncidentPriority


class AgentAction(BaseModel):
    type: AgentActionType
    missing_fields: list[str] = Field(default_factory=list)


class AgentIncidentProposal(BaseModel):
    should_create: bool
    pest_type: str | None = None
    location: str | None = None
    affected_area: str | None = None
    priority: IncidentPriority = "medium"
    summary: str | None = None
    id: str | None = None
    conversation_id: str | None = None
    status: str | None = None


class AgentResponse(BaseModel):
    reply: str
    action: AgentAction
    incident: AgentIncidentProposal | None = None
    metadata: dict[str, Any] = Field(default_factory=dict, exclude=True)
