import anyio
from fastapi.testclient import TestClient

from app.dependencies import admin_auth
from app.main import app
from app.routes import tools as tools_route
from app.schemas.tool_harness import ToolExecutionRecord
from app.services.mock_firestore_service import MockFirestoreService
from app.services.tool_execution_service import ToolExecutionService

client = TestClient(app)


def _record(**overrides: object) -> ToolExecutionRecord:
    payload = {
        "tool_request_id": "request-1",
        "tool_decision_id": "decision-1",
        "trace_id": "trace-1",
        "conversation_id": "telegram:user-1",
        "tool_name": "gmail.create_draft",
        "provider": "gmail",
        "action": "create_draft",
        "risk_level": 1,
        "requires_approval": False,
        "decision": "convert_to_draft",
        "execution_status": "draft_proposed",
        "review_status": "proposed",
        "executed": False,
        "external_effect": False,
        "metadata": {
            "external_tools_executed": False,
            "payload": {
                "recipient": "cliente@example.test",
                "subject": "Resumen",
                "body": "Borrador de prueba.",
            },
        },
    }
    payload.update(overrides)
    return ToolExecutionRecord(**payload)


async def _seed_records(service: ToolExecutionService) -> tuple[str, str]:
    gmail_record = await service.create_execution_record(_record())
    calendar_record = await service.create_execution_record(
        _record(
            tool_request_id="request-2",
            tool_decision_id="decision-2",
            trace_id="trace-2",
            tool_name="calendar.propose_event",
            provider="calendar",
            action="propose_event",
            risk_level=3,
            requires_approval=True,
            decision="require_human_approval",
            execution_status="pending_human_approval",
        )
    )
    return gmail_record.id, calendar_record.id


def test_get_tool_executions_lists_records(monkeypatch) -> None:
    service = ToolExecutionService(MockFirestoreService())
    monkeypatch.setattr(tools_route, "tool_execution_service", service)
    anyio.run(_seed_records, service)

    response = client.get("/tools/executions")

    body = response.json()
    assert response.status_code == 200
    assert len(body) == 2
    assert all(item["executed"] is False for item in body)
    assert "secret" not in response.text.casefold()


def test_get_tool_executions_filters_records(monkeypatch) -> None:
    service = ToolExecutionService(MockFirestoreService())
    monkeypatch.setattr(tools_route, "tool_execution_service", service)
    gmail_id, calendar_id = anyio.run(_seed_records, service)

    provider_response = client.get("/tools/executions?provider=calendar")
    risk_response = client.get("/tools/executions?risk_level=1")
    approval_response = client.get("/tools/executions?requires_approval=true")

    assert provider_response.status_code == 200
    assert [item["id"] for item in provider_response.json()] == [calendar_id]
    assert risk_response.status_code == 200
    assert [item["id"] for item in risk_response.json()] == [gmail_id]
    assert approval_response.status_code == 200
    assert [item["id"] for item in approval_response.json()] == [calendar_id]


def test_get_tool_execution_returns_detail(monkeypatch) -> None:
    service = ToolExecutionService(MockFirestoreService())
    monkeypatch.setattr(tools_route, "tool_execution_service", service)
    gmail_id, _ = anyio.run(_seed_records, service)

    response = client.get(f"/tools/executions/{gmail_id}")

    body = response.json()
    assert response.status_code == 200
    assert body["id"] == gmail_id
    assert body["tool_name"] == "gmail.create_draft"


def test_get_tool_execution_returns_404(monkeypatch) -> None:
    service = ToolExecutionService(MockFirestoreService())
    monkeypatch.setattr(tools_route, "tool_execution_service", service)

    response = client.get("/tools/executions/missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "Tool execution record not found."


def test_patch_tool_execution_updates_review_without_execution(monkeypatch) -> None:
    service = ToolExecutionService(MockFirestoreService())
    monkeypatch.setattr(tools_route, "tool_execution_service", service)
    _, calendar_id = anyio.run(_seed_records, service)

    response = client.patch(
        f"/tools/executions/{calendar_id}",
        json={
            "review_status": "approved",
            "reviewer_notes": "Aprobado como propuesta; no ejecutar todavía.",
            "reviewed_by": "qa",
            "approved_payload": {"title": "Visita propuesta"},
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["review_status"] == "approved"
    assert body["reviewer_notes"] == "Aprobado como propuesta; no ejecutar todavía."
    assert body["approved_payload"] == {"title": "Visita propuesta"}
    assert body["reviewed_at"] is not None
    assert body["executed"] is False
    assert body["external_effect"] is False


def test_patch_tool_execution_rejects_arbitrary_fields(monkeypatch) -> None:
    service = ToolExecutionService(MockFirestoreService())
    monkeypatch.setattr(tools_route, "tool_execution_service", service)
    gmail_id, _ = anyio.run(_seed_records, service)

    response = client.patch(
        f"/tools/executions/{gmail_id}",
        json={"executed": True, "external_effect": True},
    )

    assert response.status_code == 422


def test_execute_tool_execution_requires_approved_review(monkeypatch) -> None:
    service = ToolExecutionService(MockFirestoreService())
    monkeypatch.setattr(tools_route, "tool_execution_service", service)
    gmail_id, _ = anyio.run(_seed_records, service)

    response = client.post(f"/tools/executions/{gmail_id}/execute")

    assert response.status_code == 409
    assert "approved" in response.json()["detail"]


def test_execute_tool_execution_requires_enabled_gmail_flags(monkeypatch) -> None:
    service = ToolExecutionService(MockFirestoreService())
    monkeypatch.setattr(tools_route, "tool_execution_service", service)
    monkeypatch.setattr(tools_route, "gmail_tool_executor", None)
    record = anyio.run(
        service.create_execution_record,
        _record(review_status="approved"),
    )

    response = client.post(f"/tools/executions/{record.id}/execute")

    assert response.status_code == 403
    assert "disabled" in response.json()["detail"].casefold()


def test_execute_tool_execution_creates_gmail_draft_with_mock_executor(monkeypatch) -> None:
    class MockGmailExecutor:
        async def create_draft(self, payload: dict) -> dict:
            assert payload["recipient"] == "cliente@example.test"
            return {
                "provider": "gmail",
                "draft_id": "draft-1",
                "message_id": "message-1",
            }

    service = ToolExecutionService(MockFirestoreService())
    monkeypatch.setattr(tools_route, "tool_execution_service", service)
    monkeypatch.setattr(tools_route, "gmail_tool_executor", MockGmailExecutor())
    record = anyio.run(
        service.create_execution_record,
        _record(review_status="approved"),
    )

    response = client.post(f"/tools/executions/{record.id}/execute")

    body = response.json()
    assert response.status_code == 200
    assert body["executed"] is True
    assert body["external_effect"] is True
    assert body["execution_status"] == "executed"
    assert body["execution_result"] == {
        "provider": "gmail",
        "draft_id": "draft-1",
        "message_id": "message-1",
    }
    assert "Borrador de prueba" not in str(body["execution_result"])


def test_execute_tool_execution_uses_approved_payload_when_present(monkeypatch) -> None:
    class MockGmailExecutor:
        async def create_draft(self, payload: dict) -> dict:
            assert payload["subject"] == "Asunto aprobado"
            return {"provider": "gmail", "draft_id": "draft-approved"}

    service = ToolExecutionService(MockFirestoreService())
    monkeypatch.setattr(tools_route, "tool_execution_service", service)
    monkeypatch.setattr(tools_route, "gmail_tool_executor", MockGmailExecutor())
    record = anyio.run(
        service.create_execution_record,
        _record(
            review_status="approved",
            approved_payload={
                "recipient": "cliente@example.test",
                "subject": "Asunto aprobado",
                "body": "Cuerpo aprobado.",
            },
        ),
    )

    response = client.post(f"/tools/executions/{record.id}/execute")

    assert response.status_code == 200
    assert response.json()["execution_result"]["draft_id"] == "draft-approved"


def test_execute_tool_execution_rejects_send_email(monkeypatch) -> None:
    service = ToolExecutionService(MockFirestoreService())
    monkeypatch.setattr(tools_route, "tool_execution_service", service)
    record = anyio.run(
        service.create_execution_record,
        _record(
            review_status="approved",
            tool_name="gmail.send_email",
            action="send_email",
            decision="deny",
            execution_status="blocked",
        ),
    )

    response = client.post(f"/tools/executions/{record.id}/execute")

    assert response.status_code == 403
    assert "not allowed by policy" in response.json()["detail"]


def test_execute_tool_execution_requires_human_review_when_policy_requires_it(
    monkeypatch,
) -> None:
    class MockGmailExecutor:
        async def create_draft(self, payload: dict) -> dict:
            raise AssertionError("Policy should block before executor is called.")

    service = ToolExecutionService(MockFirestoreService())
    monkeypatch.setattr(tools_route, "tool_execution_service", service)
    monkeypatch.setattr(tools_route, "gmail_tool_executor", MockGmailExecutor())
    record = anyio.run(
        service.create_execution_record,
        _record(
            review_status="approved",
            tool_name="suggest_visit_tool",
            action="suggest_visit",
            provider="llm",
            decision="require_human_approval",
            execution_status="pending_human_approval",
        ),
    )

    response = client.post(f"/tools/executions/{record.id}/execute")

    assert response.status_code == 409
    assert "requires human review" in response.json()["detail"]


def test_execute_tool_execution_does_not_run_twice(monkeypatch) -> None:
    class MockGmailExecutor:
        async def create_draft(self, payload: dict) -> dict:
            return {"provider": "gmail", "draft_id": "draft-1"}

    service = ToolExecutionService(MockFirestoreService())
    monkeypatch.setattr(tools_route, "tool_execution_service", service)
    monkeypatch.setattr(tools_route, "gmail_tool_executor", MockGmailExecutor())
    record = anyio.run(
        service.create_execution_record,
        _record(review_status="approved"),
    )

    first_response = client.post(f"/tools/executions/{record.id}/execute")
    second_response = client.post(f"/tools/executions/{record.id}/execute")

    assert first_response.status_code == 200
    assert second_response.status_code == 409
    assert "already" in second_response.json()["detail"]


def test_tool_executions_endpoint_requires_admin_auth(monkeypatch) -> None:
    monkeypatch.setattr(admin_auth.settings, "require_admin_auth", True)
    monkeypatch.setattr(admin_auth.settings, "admin_api_key", "test-admin-key")

    response = client.get("/tools/executions")

    assert response.status_code == 401
    assert "test-admin-key" not in response.text


def test_tool_executions_endpoint_accepts_admin_auth(monkeypatch) -> None:
    service = ToolExecutionService(MockFirestoreService())
    monkeypatch.setattr(tools_route, "tool_execution_service", service)
    monkeypatch.setattr(admin_auth.settings, "require_admin_auth", True)
    monkeypatch.setattr(admin_auth.settings, "admin_api_key", "test-admin-key")

    response = client.get(
        "/tools/executions",
        headers={"X-Admin-API-Key": "test-admin-key"},
    )

    assert response.status_code == 200
