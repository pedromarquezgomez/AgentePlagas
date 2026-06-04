from typing import Any
from pydantic import BaseModel, Field

class VisitProposal(BaseModel):
    incident_id: str
    customer_name: str
    customer_email: str | None = None
    location: str
    visit_type: str
    duration_minutes: int = 60
    proposed_slots: list[str] = Field(default_factory=list)

class CalendarEventDraft(BaseModel):
    title: str
    start_time: str  # ISO timestamp
    end_time: str    # ISO timestamp
    location: str | None = None
    description: str | None = None
    attendees: list[str] = Field(default_factory=list)

class SelectedVisitSlot(BaseModel):
    slot_index: int
    start_time: str
    end_time: str
    selection_text: str | None = None
