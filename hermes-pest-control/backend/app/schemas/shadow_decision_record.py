from typing import Any

from pydantic import BaseModel, Field

from app.schemas.types import AgentActionType, Channel, IncidentPriority


class ShadowDecisionRecord(BaseModel):
    id: str | None = None
    trace_id: str
    conversation_id: str
    channel: Channel
    primary_hermes_mode: str
    shadow_hermes_mode: str
    primary_action_type: AgentActionType
    shadow_action_type: AgentActionType | None = None
    primary_priority: IncidentPriority | None = None
    shadow_priority: IncidentPriority | None = None
    primary_pest_type: str | None = None
    shadow_pest_type: str | None = None
    primary_should_create: bool
    shadow_should_create: bool | None = None
    agreement_summary: str
    differences: dict[str, Any] = Field(default_factory=dict)
    shadow_fallback_used: bool = False
    shadow_error: str | None = None
    created_at: Any | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ShadowDecisionRecordCreate(BaseModel):
    trace_id: str
    conversation_id: str
    channel: Channel
    primary_hermes_mode: str
    shadow_hermes_mode: str
    primary_action_type: AgentActionType
    shadow_action_type: AgentActionType | None = None
    primary_priority: IncidentPriority | None = None
    shadow_priority: IncidentPriority | None = None
    primary_pest_type: str | None = None
    shadow_pest_type: str | None = None
    primary_should_create: bool
    shadow_should_create: bool | None = None
    agreement_summary: str
    differences: dict[str, Any] = Field(default_factory=dict)
    shadow_fallback_used: bool = False
    shadow_error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
