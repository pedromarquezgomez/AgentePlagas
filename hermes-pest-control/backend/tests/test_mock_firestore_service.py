import pytest

from app.services.mock_firestore_service import MockFirestoreService


@pytest.mark.asyncio
async def test_mock_firestore_service_create_document() -> None:
    service = MockFirestoreService()

    document = await service.create_document(
        "conversations",
        {"channel": "telegram"},
        document_id="telegram:test-user-1",
    )

    assert document["id"] == "telegram:test-user-1"
    assert document["channel"] == "telegram"
    assert document["created_at"] is not None
    assert document["updated_at"] is not None


@pytest.mark.asyncio
async def test_mock_firestore_service_get_document() -> None:
    service = MockFirestoreService()
    await service.create_document(
        "conversations",
        {"channel": "telegram"},
        document_id="telegram:test-user-1",
    )

    document = await service.get_document("conversations", "telegram:test-user-1")

    assert document is not None
    assert document["id"] == "telegram:test-user-1"


@pytest.mark.asyncio
async def test_mock_firestore_service_update_document() -> None:
    service = MockFirestoreService()
    await service.create_document(
        "conversations",
        {"channel": "telegram", "status": "active"},
        document_id="telegram:test-user-1",
    )

    document = await service.update_document(
        "conversations",
        "telegram:test-user-1",
        {"status": "closed"},
    )

    assert document["id"] == "telegram:test-user-1"
    assert document["channel"] == "telegram"
    assert document["status"] == "closed"

