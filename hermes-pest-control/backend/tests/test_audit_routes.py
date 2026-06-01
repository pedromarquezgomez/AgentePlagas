from fastapi.testclient import TestClient

from app.main import app
from app.routes import audit as audit_route
from app.schemas.decision_record import DecisionRecordCreate
from app.schemas.shadow_decision_record import ShadowDecisionRecordCreate
from app.services.decision_audit_service import DecisionAuditService
from app.services.mock_firestore_service import MockFirestoreService
from app.services.shadow_decision_service import ShadowDecisionService


client = TestClient(app)


async def _seed_records(service: DecisionAuditService) -> tuple[str, str]:
    create_record = await service.create_decision_record(
        DecisionRecordCreate(
            trace_id="trace-create",
            conversation_id="telegram:user-create",
            message_id="message-create",
            incident_id="incident-create",
            channel="telegram",
            hermes_mode="mock",
            action_type="create_incident",
            incident_should_create=True,
            pest_type="cucarachas",
            priority="high",
            fallback_used=False,
        )
    )
    fallback_record = await service.create_decision_record(
        DecisionRecordCreate(
            trace_id="trace-fallback",
            conversation_id="telegram:user-fallback",
            message_id="message-fallback",
            channel="telegram",
            hermes_mode="real",
            action_type="escalate_to_human",
            incident_should_create=True,
            priority="medium",
            fallback_used=True,
            fallback_reason="hermes_service_error",
        )
    )
    return create_record.id, fallback_record.id


def test_get_decision_records_lists_records(monkeypatch) -> None:
    import anyio

    firestore_service = MockFirestoreService()
    service = DecisionAuditService(firestore_service)
    monkeypatch.setattr(audit_route, "decision_audit_service", service)
    anyio.run(_seed_records, service)

    response = client.get("/audit/decisions")

    body = response.json()
    assert response.status_code == 200
    assert len(body) == 2
    assert "secret" not in response.text.casefold()


def test_get_decision_records_filters_by_action_type(monkeypatch) -> None:
    import anyio

    firestore_service = MockFirestoreService()
    service = DecisionAuditService(firestore_service)
    monkeypatch.setattr(audit_route, "decision_audit_service", service)
    create_id, _ = anyio.run(_seed_records, service)

    response = client.get("/audit/decisions?action_type=create_incident")

    body = response.json()
    assert response.status_code == 200
    assert len(body) == 1
    assert body[0]["id"] == create_id
    assert body[0]["action_type"] == "create_incident"


def test_get_decision_records_filters_by_fallback_used(monkeypatch) -> None:
    import anyio

    firestore_service = MockFirestoreService()
    service = DecisionAuditService(firestore_service)
    monkeypatch.setattr(audit_route, "decision_audit_service", service)
    _, fallback_id = anyio.run(_seed_records, service)

    response = client.get("/audit/decisions?fallback_used=true")

    body = response.json()
    assert response.status_code == 200
    assert len(body) == 1
    assert body[0]["id"] == fallback_id
    assert body[0]["fallback_used"] is True


def test_get_decision_record_returns_detail(monkeypatch) -> None:
    import anyio

    firestore_service = MockFirestoreService()
    service = DecisionAuditService(firestore_service)
    monkeypatch.setattr(audit_route, "decision_audit_service", service)
    decision_id, _ = anyio.run(_seed_records, service)

    response = client.get(f"/audit/decisions/{decision_id}")

    body = response.json()
    assert response.status_code == 200
    assert body["id"] == decision_id
    assert body["trace_id"] == "trace-create"
    assert body["response_contract_version"] == "AgentResponse.v1"


def test_get_decision_record_returns_404_for_missing_record(monkeypatch) -> None:
    firestore_service = MockFirestoreService()
    service = DecisionAuditService(firestore_service)
    monkeypatch.setattr(audit_route, "decision_audit_service", service)

    response = client.get("/audit/decisions/missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "Decision record not found."


async def _seed_shadow_records(service: ShadowDecisionService) -> tuple[str, str]:
    create_record = await service.create_shadow_record(
        ShadowDecisionRecordCreate(
            trace_id="trace-shadow-1",
            conversation_id="telegram:user-shadow-1",
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
    difference_record = await service.create_shadow_record(
        ShadowDecisionRecordCreate(
            trace_id="trace-shadow-2",
            conversation_id="whatsapp:user-shadow-2",
            channel="whatsapp",
            primary_hermes_mode="mock",
            shadow_hermes_mode="real",
            primary_action_type="collect_missing_data",
            shadow_action_type="escalate_to_human",
            primary_should_create=False,
            shadow_should_create=True,
            agreement_summary="differences_detected",
            differences={"action_type": {"primary": "collect_missing_data", "shadow": "escalate_to_human"}},
        )
    )
    return create_record.id, difference_record.id


def test_get_shadow_decision_records_lists_records(monkeypatch) -> None:
    import anyio

    firestore_service = MockFirestoreService()
    service = ShadowDecisionService(firestore_service)
    monkeypatch.setattr(audit_route, "shadow_decision_service", service)
    anyio.run(_seed_shadow_records, service)

    response = client.get("/audit/shadow-decisions")

    body = response.json()
    assert response.status_code == 200
    assert len(body) == 2
    assert "secret" not in response.text.casefold()


def test_get_shadow_decision_records_filters_by_channel(monkeypatch) -> None:
    import anyio

    firestore_service = MockFirestoreService()
    service = ShadowDecisionService(firestore_service)
    monkeypatch.setattr(audit_route, "shadow_decision_service", service)
    _, difference_id = anyio.run(_seed_shadow_records, service)

    response = client.get("/audit/shadow-decisions?channel=whatsapp")

    body = response.json()
    assert response.status_code == 200
    assert len(body) == 1
    assert body[0]["id"] == difference_id
    assert body[0]["channel"] == "whatsapp"


def test_get_shadow_decision_records_filters_by_shadow_action_type(monkeypatch) -> None:
    import anyio

    firestore_service = MockFirestoreService()
    service = ShadowDecisionService(firestore_service)
    monkeypatch.setattr(audit_route, "shadow_decision_service", service)
    _, difference_id = anyio.run(_seed_shadow_records, service)

    response = client.get(
        "/audit/shadow-decisions?shadow_action_type=escalate_to_human"
    )

    body = response.json()
    assert response.status_code == 200
    assert len(body) == 1
    assert body[0]["id"] == difference_id
    assert body[0]["shadow_action_type"] == "escalate_to_human"


def test_get_shadow_decision_record_returns_detail(monkeypatch) -> None:
    import anyio

    firestore_service = MockFirestoreService()
    service = ShadowDecisionService(firestore_service)
    monkeypatch.setattr(audit_route, "shadow_decision_service", service)
    shadow_id, _ = anyio.run(_seed_shadow_records, service)

    response = client.get(f"/audit/shadow-decisions/{shadow_id}")

    body = response.json()
    assert response.status_code == 200
    assert body["id"] == shadow_id
    assert body["trace_id"] == "trace-shadow-1"
    assert body["agreement_summary"] == "full_agreement"


def test_get_shadow_decision_record_returns_404_for_missing_record(monkeypatch) -> None:
    firestore_service = MockFirestoreService()
    service = ShadowDecisionService(firestore_service)
    monkeypatch.setattr(audit_route, "shadow_decision_service", service)

    response = client.get("/audit/shadow-decisions/missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "Shadow decision record not found."
