from datetime import datetime, timezone

from pydantic import BaseModel

from app.services.firestore_service import FirestoreService


class ExamplePayload(BaseModel):
    name: str
    enabled: bool
    count: int
    tags: list[str]
    metadata: dict[str, str]
    created_at: datetime


def test_firestore_service_to_dict_serializes_pydantic_model() -> None:
    service = FirestoreService.__new__(FirestoreService)
    payload = ExamplePayload(
        name="check",
        enabled=True,
        count=2,
        tags=["a", "b"],
        metadata={"source": "test"},
        created_at=datetime(2026, 5, 31, tzinfo=timezone.utc),
    )

    data = service._to_dict(payload)

    assert data == {
        "name": "check",
        "enabled": True,
        "count": 2,
        "tags": ["a", "b"],
        "metadata": {"source": "test"},
        "created_at": datetime(2026, 5, 31, tzinfo=timezone.utc),
    }


def test_firestore_service_to_dict_accepts_dict() -> None:
    service = FirestoreService.__new__(FirestoreService)
    payload = {
        "name": "check",
        "enabled": True,
        "metadata": {"source": "test"},
        "tags": ["a", "b"],
    }

    data = service._to_dict(payload)

    assert data == payload
    assert data is not payload
