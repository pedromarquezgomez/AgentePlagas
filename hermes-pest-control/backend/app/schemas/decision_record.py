from typing import Any

from pydantic import BaseModel, Field

from app.schemas.types import AgentActionType, Channel, IncidentPriority


class DecisionRecord(BaseModel):
    id: str | None = None
    trace_id: str
    conversation_id: str
    message_id: str | None = None
    incident_id: str | None = None
    channel: Channel
    hermes_mode: str
    action_type: AgentActionType
    incident_should_create: bool
    pest_type: str | None = None
    priority: IncidentPriority | None = None
    fallback_used: bool = False
    fallback_reason: str | None = None
    prompt_version: str
    skill_version: str
    response_contract_version: str
    pilot_mode_enabled: bool = False
    pilot_used: bool = False
    pilot_blocked: bool = False
    pilot_blocked_reason: str | None = None
    pilot_route: str | None = None
    pilot_risk_flags: list[str] = Field(default_factory=list)
    pilot_policy_rule: str | None = None
    created_at: Any | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DecisionRecordCreate(BaseModel):
    trace_id: str
    conversation_id: str
    message_id: str | None = None
    incident_id: str | None = None
    channel: Channel
    hermes_mode: str
    action_type: AgentActionType
    incident_should_create: bool
    pest_type: str | None = None
    priority: IncidentPriority | None = None
    fallback_used: bool = False
    fallback_reason: str | None = None
    prompt_version: str = "hermes_system_prompt.v1"
    skill_version: str = "pest_control_intake.v1"
    response_contract_version: str = "AgentResponse.v1"
    pilot_mode_enabled: bool = False
    pilot_used: bool = False
    pilot_blocked: bool = False
    pilot_blocked_reason: str | None = None
    pilot_route: str | None = None
    pilot_risk_flags: list[str] = Field(default_factory=list)
    pilot_policy_rule: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
