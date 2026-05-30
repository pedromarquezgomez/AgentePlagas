from uuid import uuid4

from app.schemas.incident import Incident, IncidentDraft
from app.services.firestore_service import FirestoreService


class IncidentService:
    def __init__(self, firestore_service: FirestoreService | None = None) -> None:
        self.firestore_service = firestore_service or FirestoreService()

    async def create_incident(self, incident_draft: IncidentDraft) -> Incident:
        incident = Incident(
            id=str(uuid4()),
            conversation_id=incident_draft.conversation_id,
            channel=incident_draft.channel,
            pest_type=incident_draft.pest_type,
            location=incident_draft.location,
            affected_area=incident_draft.affected_area,
            priority=incident_draft.priority,
            status="pending_review",
            summary=incident_draft.summary,
            metadata=incident_draft.metadata,
        )
        await self.firestore_service.create_document("incidents", incident.model_dump())
        return incident
