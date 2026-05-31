import pytest

from app.schemas.human_review import HumanReviewItemCreate
from app.services.human_review_service import (
    HumanReviewItemNotFoundError,
    HumanReviewService,
)
from app.services.mock_firestore_service import MockFirestoreService


def _review_item(reason: str = "agent_escalation") -> HumanReviewItemCreate:
    return HumanReviewItemCreate(
        trace_id="trace-human-review",
        conversation_id="telegram:human-review-user",
        incident_id="incident-1",
        decision_record_id="decision-1",
        channel="telegram",
        reason=reason,
        priority="high",
        summary="Caso requiere revisión humana.",
    )


@pytest.mark.asyncio
async def test_create_review_item() -> None:
    service = HumanReviewService(MockFirestoreService())

    item = await service.create_review_item(_review_item())

    assert item.id is not None
    assert item.status == "open"
    assert item.reason == "agent_escalation"
    assert item.priority == "high"
    assert item.created_at is not None
    assert item.updated_at is not None


@pytest.mark.asyncio
async def test_list_review_items_filters_by_status_and_priority() -> None:
    service = HumanReviewService(MockFirestoreService())
    first = await service.create_review_item(_review_item())
    second = await service.create_review_item(
        HumanReviewItemCreate(
            trace_id="trace-2",
            conversation_id="telegram:second",
            channel="telegram",
            reason="fallback_used",
            priority="urgent",
            summary="Fallback requiere revisión.",
        )
    )
    await service.update_review_item(first.id, {"status": "resolved"})

    open_items = await service.list_review_items(status_filter="open")
    urgent_items = await service.list_review_items(priority="urgent")

    assert [item["id"] for item in open_items] == [second.id]
    assert [item["id"] for item in urgent_items] == [second.id]


@pytest.mark.asyncio
async def test_get_review_item_returns_detail() -> None:
    service = HumanReviewService(MockFirestoreService())
    item = await service.create_review_item(_review_item())

    detail = await service.get_review_item(item.id)

    assert detail["id"] == item.id
    assert detail["decision_record_id"] == "decision-1"


@pytest.mark.asyncio
async def test_update_review_item_marks_resolved_at() -> None:
    service = HumanReviewService(MockFirestoreService())
    item = await service.create_review_item(_review_item())

    updated = await service.update_review_item(
        item.id,
        {
            "status": "resolved",
            "assigned_to": "operador",
            "resolution_notes": "Revisado y cerrado.",
        },
    )

    assert updated["status"] == "resolved"
    assert updated["assigned_to"] == "operador"
    assert updated["resolution_notes"] == "Revisado y cerrado."
    assert updated["resolved_at"] is not None


@pytest.mark.asyncio
async def test_get_missing_review_item_raises() -> None:
    service = HumanReviewService(MockFirestoreService())

    with pytest.raises(HumanReviewItemNotFoundError):
        await service.get_review_item("missing")
