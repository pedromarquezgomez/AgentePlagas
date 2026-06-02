from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


ToolRiskLevel = Literal[0, 1, 2, 3, 4, 5]
ToolDecisionOutcome = Literal[
    "allow",
    "deny",
    "require_human_approval",
    "convert_to_draft",
    "require_more_data",
]
ToolExecutionStatus = Literal[
    "not_executed",
    "blocked",
    "draft_proposed",
    "pending_human_approval",
    "requires_more_data",
    "allowed_not_executed",
    "executed",
]
ToolReviewStatus = Literal[
    "proposed",
    "approved",
    "rejected",
    "needs_more_info",
    "dismissed",
]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ToolRequest(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    tool_name: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    action: str = Field(min_length=1)
    target: dict[str, Any] = Field(default_factory=dict)
    payload: dict[str, Any] = Field(default_factory=dict)
    risk_level: ToolRiskLevel
    requires_approval: bool
    reason: str = Field(min_length=1)
    trace_id: str = Field(min_length=1)
    conversation_id: str = Field(min_length=1)
    proposed_by: str = Field(default="nous_hermes_agent", min_length=1)
    created_at: datetime = Field(default_factory=_utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolDecision(BaseModel):
    allow: bool = False
    deny: bool = False
    require_human_approval: bool = False
    convert_to_draft: bool = False
    require_more_data: bool = False
    reason: str = Field(min_length=1)
    policy_rule: str = Field(min_length=1)
    audit_id: str = Field(default_factory=lambda: str(uuid4()))

    @model_validator(mode="after")
    def exactly_one_outcome(self) -> "ToolDecision":
        enabled = [
            self.allow,
            self.deny,
            self.require_human_approval,
            self.convert_to_draft,
            self.require_more_data,
        ]
        if sum(bool(value) for value in enabled) != 1:
            raise ValueError("ToolDecision must contain exactly one outcome.")
        return self

    @property
    def outcome(self) -> ToolDecisionOutcome:
        if self.allow:
            return "allow"
        if self.deny:
            return "deny"
        if self.require_human_approval:
            return "require_human_approval"
        if self.convert_to_draft:
            return "convert_to_draft"
        return "require_more_data"


class ToolExecutionRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    tool_request_id: str = Field(min_length=1)
    tool_decision_id: str = Field(min_length=1)
    trace_id: str = Field(min_length=1)
    conversation_id: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    action: str = Field(min_length=1)
    risk_level: ToolRiskLevel
    requires_approval: bool
    decision: ToolDecisionOutcome
    execution_status: ToolExecutionStatus
    review_status: ToolReviewStatus = "proposed"
    reviewer_notes: str | None = None
    reviewed_by: str | None = None
    approved_payload: dict[str, Any] | None = None
    executed: bool = False
    external_effect: bool = False
    execution_result: dict[str, Any] | None = None
    execution_error: str | None = None
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime | None = None
    reviewed_at: datetime | None = None
    executed_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def external_effect_requires_execution(self) -> "ToolExecutionRecord":
        if self.external_effect and not self.executed:
            raise ValueError("external_effect cannot be true when executed is false.")
        return self


class ToolExecutionRecordUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_status: ToolReviewStatus | None = None
    reviewer_notes: str | None = None
    reviewed_by: str | None = None
    approved_payload: dict[str, Any] | None = None
