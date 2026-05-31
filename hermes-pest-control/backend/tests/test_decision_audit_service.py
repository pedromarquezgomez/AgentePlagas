import pytest

from app.schemas.decision_record import DecisionRecordCreate
from app.services.decision_audit_service import DecisionAuditService
from app.services.mock_firestore_service import MockFirestoreService


@pytest.mark.asyncio
async def test_decision_audit_service_creates_record() -> None:
    firestore_service = MockFirestoreService()
    service = DecisionAuditService(firestore_service)

    record = await service.create_decision_record(
        DecisionRecordCreate(
            trace_id="trace-1",
            conversation_id="telegram:user-1",
            message_id="message-1",
            incident_id="incident-1",
            channel="telegram",
            hermes_mode="mock",
            action_type="create_incident",
            incident_should_create=True,
            pest_type="cucarachas",
            priority="high",
            fallback_used=False,
        )
    )

    assert record.id is not None
    assert record.trace_id == "trace-1"
    assert record.conversation_id == "telegram:user-1"
    assert record.action_type == "create_incident"
    assert record.response_contract_version == "AgentResponse.v1"
    assert record.created_at is not None
