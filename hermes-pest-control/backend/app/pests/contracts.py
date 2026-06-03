from pydantic import BaseModel, Field


class PestClassification(BaseModel):
    pest_type: str | None = None
    confidence: str | None = None
    evidence: str | None = None
    detected_terms: list[str] = Field(default_factory=list)
    recommended_priority: str | None = None
    requires_human_review: bool = False
    pest_type_spanish: str | None = None

