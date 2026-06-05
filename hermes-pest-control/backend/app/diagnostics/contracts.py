from enum import Enum
from pydantic import BaseModel

class DiagnosisState(str, Enum):
    DIAGNOSIS = "diagnosis"
    INTAKE = "intake"
    OUT_OF_DOMAIN = "out_of_domain"

class DiagnosisHypothesis(BaseModel):
    pest_type: str
    label: str
    confidence: float
    evidence: list[str] = []
    questions: list[str] = []

class DiagnosisAssessment(BaseModel):
    state: DiagnosisState
    hypotheses: list[DiagnosisHypothesis] = []
    reason: str | None = None
    suggested_reply: str | None = None
    knowledge_key: str | None = None
