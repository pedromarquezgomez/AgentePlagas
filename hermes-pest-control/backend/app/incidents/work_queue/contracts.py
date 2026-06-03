from pydantic import BaseModel

class WorkQueueScore(BaseModel):
    incident_id: str | None = None
    score: float
    queue_position: int | None = None
    reason: str
