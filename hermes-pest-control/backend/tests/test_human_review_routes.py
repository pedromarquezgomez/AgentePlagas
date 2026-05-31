from fastapi.testclient import TestClient

from app.dependencies import admin_auth
from app.main import app
from app.routes import human_review as human_review_route
from app.schemas.human_review import HumanReviewItemCreate
from app.services.human_review_service import HumanReviewService
from app.services.mock_firestore_service import MockFirestoreService


client = TestClient(app)


async def _seed_review_items(service: HumanReviewService) -> tuple[str, str]:
    escalation = await service.create_review_item(
        HumanReviewItemCreate(
            trace_id="trace-escalation",
            conversation_id="telegram:escalation",
            incident_id="incident-escalation",
            decision_record_id="decision-escalation",
            channel="telegram",
            reason="agent_escalation",
            priority="high",
            summary="Escalado por Hermes.",
        )
    )
    fallback = await service.create_review_item(
        HumanReviewItemCreate(
            trace_id="trace-fallback",
            conversation_id="telegram:fallback",
            channel="telegram",
            reason="fallback_used",
            priority="urgent",
            summary="Fallback seguro.",
        )
    )
    return escalation.id, fallback.id


def test_get_human_review_lists_items(monkeypatch) -> None:
    import anyio

    service = HumanReviewService(MockFirestoreService())
    monkeypatch.setattr(human_review_route, "human_review_service", service)
    anyio.run(_seed_review_items, service)

    response = client.get("/human-review")

    body = response.json()
    assert response.status_code == 200
    assert len(body) == 2
    assert "secret" not in response.text.casefold()


def test_get_human_review_filters_by_status_and_priority(monkeypatch) -> None:
    import anyio

    service = HumanReviewService(MockFirestoreService())
    monkeypatch.setattr(human_review_route, "human_review_service", service)
    escalation_id, fallback_id = anyio.run(_seed_review_items, service)
    anyio.run(service.update_review_item, escalation_id, {"status": "in_review"})

    open_response = client.get("/human-review?status=open")
    urgent_response = client.get("/human-review?priority=urgent")

    assert open_response.status_code == 200
    assert [item["id"] for item in open_response.json()] == [fallback_id]
    assert urgent_response.status_code == 200
    assert [item["id"] for item in urgent_response.json()] == [fallback_id]


def test_get_human_review_item_returns_detail(monkeypatch) -> None:
    import anyio

    service = HumanReviewService(MockFirestoreService())
    monkeypatch.setattr(human_review_route, "human_review_service", service)
    item_id, _ = anyio.run(_seed_review_items, service)

    response = client.get(f"/human-review/{item_id}")

    body = response.json()
    assert response.status_code == 200
    assert body["id"] == item_id
    assert body["reason"] == "agent_escalation"


def test_get_human_review_item_returns_404(monkeypatch) -> None:
    service = HumanReviewService(MockFirestoreService())
    monkeypatch.setattr(human_review_route, "human_review_service", service)

    response = client.get("/human-review/missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "Human review item not found."


def test_patch_human_review_item_updates_status(monkeypatch) -> None:
    import anyio

    service = HumanReviewService(MockFirestoreService())
    monkeypatch.setattr(human_review_route, "human_review_service", service)
    item_id, _ = anyio.run(_seed_review_items, service)

    response = client.patch(
        f"/human-review/{item_id}",
        json={
            "status": "resolved",
            "assigned_to": "operador",
            "resolution_notes": "Resuelto por teléfono.",
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "resolved"
    assert body["assigned_to"] == "operador"
    assert body["resolved_at"] is not None


def test_patch_human_review_rejects_arbitrary_fields(monkeypatch) -> None:
    import anyio

    service = HumanReviewService(MockFirestoreService())
    monkeypatch.setattr(human_review_route, "human_review_service", service)
    item_id, _ = anyio.run(_seed_review_items, service)

    response = client.patch(
        f"/human-review/{item_id}",
        json={"summary": "No debe editarse desde PATCH."},
    )

    assert response.status_code == 422


def test_human_review_endpoint_requires_admin_auth(monkeypatch) -> None:
    monkeypatch.setattr(admin_auth.settings, "require_admin_auth", True)
    monkeypatch.setattr(admin_auth.settings, "admin_api_key", "test-admin-key")

    response = client.get("/human-review")

    assert response.status_code == 401
    assert "test-admin-key" not in response.text


def test_human_review_endpoint_accepts_admin_auth(monkeypatch) -> None:
    service = HumanReviewService(MockFirestoreService())
    monkeypatch.setattr(human_review_route, "human_review_service", service)
    monkeypatch.setattr(admin_auth.settings, "require_admin_auth", True)
    monkeypatch.setattr(admin_auth.settings, "admin_api_key", "test-admin-key")

    response = client.get(
        "/human-review",
        headers={"X-Admin-API-Key": "test-admin-key"},
    )

    assert response.status_code == 200
