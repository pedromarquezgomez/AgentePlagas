from pydantic import BaseModel, Field
from app.incidents.prioritization.contracts import IncidentSeverity, IncidentPriority
from app.incidents.dispatch.contracts import VisitType, TechnicianLevel, DispatchBucket


class IncidentIntakeState(BaseModel):
    pest_type: str | None = None
    pest_type_spanish: str | None = None
    location: str | None = None
    customer_name: str | None = None
    affected_area: str | None = None
    missing_fields: list[str] = Field(default_factory=list)
    ready_for_incident: bool = False
    is_legacy_flow: bool = False
    
    # Metadatos de clasificacion enriquecidos
    confidence: str | None = None
    evidence: str | None = None
    detected_terms: list[str] = Field(default_factory=list)
    recommended_priority: str | None = None
    requires_human_review: bool = False

    # Metadatos de priorizacion del Sprint 12 (Enums)
    severity: IncidentSeverity | None = None
    priority: IncidentPriority | None = None
    response_hours: int | None = None
    assessment_reason: str | None = None

    # Metadatos de dispatch del Sprint 13 (Enums)
    visit_type: VisitType | None = None
    technician_level: TechnicianLevel | None = None
    dispatch_bucket: DispatchBucket | None = None
    sla_hours: int | None = None

