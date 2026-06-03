from pydantic import BaseModel, Field


class IncidentIntakeState(BaseModel):
    pest_type: str | None = None
    location: str | None = None
    customer_name: str | None = None
    missing_fields: list[str] = Field(default_factory=list)
    ready_for_incident: bool = False
