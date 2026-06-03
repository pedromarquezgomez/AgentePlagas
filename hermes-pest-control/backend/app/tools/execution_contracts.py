from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ToolExecutionStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"
    EXECUTED = "executed"
    FAILED = "failed"


class ToolExecutionRequest(BaseModel):
    execution_id: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    requested_by: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_utc_now)
    trace_id: str | None = None
    conversation_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolExecutionResult(BaseModel):
    execution_id: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    status: ToolExecutionStatus
    message: str = Field(min_length=1)
    result: dict[str, Any] = Field(default_factory=dict)
    executed_at: datetime = Field(default_factory=_utc_now)


class ToolExecutionError(BaseModel):
    execution_id: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    error_code: str = Field(min_length=1)
    error_message: str = Field(min_length=1)
