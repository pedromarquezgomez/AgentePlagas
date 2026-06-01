import pytest

from app.schemas.shadow_decision_record import ShadowDecisionRecordCreate
from app.services.mock_firestore_service import MockFirestoreService
from app.services.shadow_decision_service import ShadowDecisionService


@pytest.mark.asyncio
async def test_shadow_decision_service_creates_record() -> None:
    firestore_service = MockFirestoreService()
    service = ShadowDecisionService(firestore_service)

    record = await service.create_shadow_record(
        ShadowDecisionRecordCreate(
            trace_id="trace-1",
            conversation_id="telegram:user-1",
            channel="telegram",
            primary_hermes_mode="mock",
            shadow_hermes_mode="real",
            primary_action_type="create_incident",
            shadow_action_type="create_incident",
            primary_priority="high",
            shadow_priority="high",
            primary_pest_type="cucarachas",
            shadow_pest_type="cucarachas",
            primary_should_create=True,
            shadow_should_create=True,
            agreement_summary="full_agreement",
        )
    )

    stored = await service.get_shadow_record(record.id)

    assert stored["id"] == record.id
    assert stored["trace_id"] == "trace-1"
    assert stored["agreement_summary"] == "full_agreement"


@pytest.mark.asyncio
async def test_shadow_decision_service_filters_records() -> None:
    firestore_service = MockFirestoreService()
    service = ShadowDecisionService(firestore_service)
    await service.create_shadow_record(
        ShadowDecisionRecordCreate(
            trace_id="trace-1",
            conversation_id="telegram:user-1",
            channel="telegram",
            primary_hermes_mode="mock",
            shadow_hermes_mode="real",
            primary_action_type="create_incident",
            shadow_action_type="create_incident",
            primary_should_create=True,
            shadow_should_create=True,
            agreement_summary="full_agreement",
        )
    )
    await service.create_shadow_record(
        ShadowDecisionRecordCreate(
            trace_id="trace-2",
            conversation_id="whatsapp:user-2",
            channel="whatsapp",
            primary_hermes_mode="mock",
            shadow_hermes_mode="real",
            primary_action_type="collect_missing_data",
            shadow_action_type="escalate_to_human",
            primary_should_create=False,
            shadow_should_create=True,
            agreement_summary="differences_detected",
        )
    )

    records = await service.list_shadow_records(
        channel="whatsapp",
        shadow_action_type="escalate_to_human",
    )

    assert len(records) == 1
    assert records[0]["conversation_id"] == "whatsapp:user-2"
