from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class PolicyDecision(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_HUMAN_REVIEW = "REQUIRE_HUMAN_REVIEW"


class PolicyContext(BaseModel):
    channel: str | None = None
    user_id: str | None = None
    incident_id: str | None = None
    requested_tool: str = Field(min_length=1)
    requested_action: str | None = None
    source_provider: str = Field(default="unknown", min_length=1)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PolicyEvaluation(BaseModel):
    decision: PolicyDecision
    policy_rule: str
    reason: str
