from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AuditEventType(str, Enum):
    PROVIDER_SELECTED = "provider_selected"
    TOOL_PROPOSED = "tool_proposed"
    POLICY_EVALUATED = "policy_evaluated"
    TOOL_EXECUTION_STARTED = "tool_execution_started"
    TOOL_EXECUTION_COMPLETED = "tool_execution_completed"
    TOOL_EXECUTION_FAILED = "tool_execution_failed"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    INCIDENT_PRIORITIZED = "incident_prioritized"
    INCIDENT_DISPATCH_ASSESSED = "incident_dispatch_assessed"



class AuditEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: AuditEventType
    timestamp: datetime = Field(default_factory=_utc_now)
    execution_id: str | None = None
    tool_name: str | None = None
    provider: str | None = None
    user_id: str | None = None
    channel: str | None = None
    policy_decision: str | None = None
    status: str | None = None
    message: str = Field(default="", max_length=500)
    metadata: dict[str, Any] = Field(default_factory=dict)
