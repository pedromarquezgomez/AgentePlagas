from enum import Enum

from pydantic import BaseModel


class SLAStatus(str, Enum):
    ON_TRACK = "ON_TRACK"
    AT_RISK = "AT_RISK"
    BREACHED = "BREACHED"
    COMPLETED = "COMPLETED"


class SLAAssessment(BaseModel):
    incident_id: str | None = None
    sla_status: SLAStatus
    elapsed_hours: float
    remaining_hours: float | None = None
    breach_hours: float | None = None
    is_overdue: bool = False
    reason: str
