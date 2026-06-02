import anyio

from app.services.mock_firestore_service import MockFirestoreService
from app.services.tool_execution_service import ToolExecutionService
from scripts.seed_tool_execution_records import (
    build_seed_records,
    seed_tool_execution_records,
)


def test_seed_builds_valid_tool_execution_records() -> None:
    records = build_seed_records()

    by_tool = {record.tool_name: record for record in records}
    assert len(records) == 6
    assert by_tool["gmail.create_draft"].decision == "convert_to_draft"
    assert by_tool["gmail.send_email"].decision == "deny"
    assert by_tool["calendar.propose_event"].decision == "require_human_approval"
    assert by_tool["telegram.draft_message"].decision == "require_human_approval"
    assert by_tool["whatsapp.draft_message"].decision == "deny"
    assert by_tool["firestore.direct_write"].decision == "deny"
    assert all(record.executed is False for record in records)
    assert all(record.external_effect is False for record in records)
    assert all(record.review_status == "proposed" for record in records)


def test_seed_persists_records_with_mock_firestore() -> None:
    service = ToolExecutionService(MockFirestoreService())

    created = anyio.run(seed_tool_execution_records, service)
    stored = anyio.run(lambda: service.list_execution_records(limit=20))

    assert len(created) == 6
    assert len(stored) == 6
    assert {record["tool_name"] for record in stored} == {
        "gmail.create_draft",
        "gmail.send_email",
        "calendar.propose_event",
        "telegram.draft_message",
        "whatsapp.draft_message",
        "firestore.direct_write",
    }
    assert all(record["executed"] is False for record in stored)
    assert all(record["external_effect"] is False for record in stored)


def test_seed_records_include_policy_and_safe_payload_metadata() -> None:
    records = build_seed_records()

    for record in records:
        assert record.metadata["external_tools_executed"] is False
        assert "policy_rule" in record.metadata
        assert "payload" in record.metadata
        assert "secret" not in str(record.metadata).casefold()


def test_seed_can_prepare_approved_gmail_draft(monkeypatch) -> None:
    monkeypatch.setenv("SEED_APPROVED_GMAIL_DRAFT", "true")
    monkeypatch.setenv("GMAIL_TEST_DRAFT_RECIPIENT", "cliente@example.test")

    records = build_seed_records()
    gmail_record = next(record for record in records if record.tool_name == "gmail.create_draft")

    assert gmail_record.review_status == "approved"
    assert gmail_record.reviewed_by == "seed_tool_execution_records"
    assert gmail_record.approved_payload == {
        "recipient": "cliente@example.test",
        "subject": "Prueba controlada Hermes Gmail draft",
        "body": "Borrador de prueba creado desde Acciones IA. No enviar este correo.",
    }
    assert gmail_record.executed is False
    assert gmail_record.external_effect is False
