from enum import Enum
from pydantic import BaseModel


class VisitType(str, Enum):
    INSPECTION = "INSPECTION"
    TREATMENT = "TREATMENT"
    URGENT_TREATMENT = "URGENT_TREATMENT"
    FOLLOW_UP = "FOLLOW_UP"
    HUMAN_REVIEW = "HUMAN_REVIEW"


class TechnicianLevel(str, Enum):
    JUNIOR = "JUNIOR"
    STANDARD = "STANDARD"
    SENIOR = "SENIOR"
    SPECIALIST = "SPECIALIST"


class DispatchBucket(str, Enum):
    URGENT_24H = "URGENT_24H"
    NEXT_48H = "NEXT_48H"
    THIS_WEEK = "THIS_WEEK"
    PLANNED = "PLANNED"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class DispatchAssessment(BaseModel):
    visit_type: VisitType
    technician_level: TechnicianLevel
    dispatch_bucket: DispatchBucket
    sla_hours: int | None = None
    reason: str | None = None
