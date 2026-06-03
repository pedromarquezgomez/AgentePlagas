from enum import Enum
from pydantic import BaseModel


class IncidentSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class IncidentPriority(str, Enum):
    URGENT = "URGENT"
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"


class IncidentAssessment(BaseModel):
    incident_severity: IncidentSeverity
    incident_priority: IncidentPriority
    requires_human_review: bool = False
    reason: str | None = None
    evidence: str | None = None
    recommended_response_hours: int | None = None
