from pydantic import BaseModel, Field


class IncidentIntakeState(BaseModel):
    pest_type: str | None = None
    pest_type_spanish: str | None = None
    location: str | None = None
    customer_name: str | None = None
    affected_area: str | None = None
    missing_fields: list[str] = Field(default_factory=list)
    ready_for_incident: bool = False
    is_sprint10_flow: bool = False
