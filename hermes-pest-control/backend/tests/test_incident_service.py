import pytest

from app.schemas.incident import IncidentDraft
from app.services.incident_service import IncidentService
from app.services.mock_firestore_service import MockFirestoreService


@pytest.mark.asyncio
async def test_incident_service_creates_pending_review_incident_from_draft() -> None:
    firestore_service = MockFirestoreService()
    service = IncidentService(firestore_service)
    draft = IncidentDraft(
        conversation_id="telegram:12345",
        channel="telegram",
        pest_type="cucarachas",
        location="Torremolinos",
        affected_area="cocina",
        priority="high",
        summary="Cliente informa de cucarachas en cocina.",
    )

    incident = await service.create_incident(draft)

    assert incident.id is not None
    assert incident.conversation_id == "telegram:12345"
    assert incident.status == "pending_review"
    assert incident.channel == "telegram"
    assert incident.pest_type == "cucarachas"

    persisted_incident = await firestore_service.get_document("incidents", incident.id)
    assert persisted_incident is not None
    assert persisted_incident["status"] == "pending_review"
