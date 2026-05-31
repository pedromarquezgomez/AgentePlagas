from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


class MockFirestoreService:
    def __init__(self) -> None:
        self._collections: dict[str, dict[str, dict[str, Any]]] = {}

    async def create_document(
        self,
        collection: str,
        data: Any,
        document_id: str | None = None,
    ) -> dict[str, Any]:
        payload = self._to_dict(data)
        now = self._now()
        resolved_document_id = str(document_id or payload.get("id") or uuid4())

        document = deepcopy(payload)
        document["id"] = resolved_document_id
        document.setdefault("created_at", now)
        document.setdefault("updated_at", now)

        self._collections.setdefault(collection, {})[resolved_document_id] = document
        return deepcopy(document)

    async def get_document(
        self,
        collection: str,
        document_id: str,
    ) -> dict[str, Any] | None:
        document = self._collections.get(collection, {}).get(str(document_id))
        return deepcopy(document) if document is not None else None

    async def update_document(
        self,
        collection: str,
        document_id: str,
        data: Any,
    ) -> dict[str, Any]:
        now = self._now()
        payload = self._to_dict(data)
        current = self._collections.setdefault(collection, {}).get(str(document_id), {})

        updated = {
            **deepcopy(current),
            **deepcopy(payload),
            "id": str(document_id),
            "updated_at": now,
        }
        updated.setdefault("created_at", current.get("created_at", now))
        self._collections[collection][str(document_id)] = updated
        return deepcopy(updated)

    async def list_documents(
        self,
        collection: str,
        filters: dict[str, Any] | list[tuple[str, str, Any]] | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        documents = [
            deepcopy(document)
            for document in self._collections.get(collection, {}).values()
            if self._matches_filters(document, filters)
        ]
        return documents[:limit] if limit is not None else documents

    async def append_to_subcollection(
        self,
        parent_collection: str,
        parent_id: str,
        subcollection: str,
        data: Any,
    ) -> dict[str, Any]:
        collection_key = f"{parent_collection}/{parent_id}/{subcollection}"
        return await self.create_document(collection_key, data)

    def _to_dict(self, data: Any) -> dict[str, Any]:
        if hasattr(data, "model_dump"):
            return data.model_dump(mode="python")
        if isinstance(data, dict):
            return dict(data)
        raise TypeError(
            f"Mock Firestore data must be a dict or Pydantic model: {type(data)!r}"
        )

    def _matches_filters(
        self,
        document: dict[str, Any],
        filters: dict[str, Any] | list[tuple[str, str, Any]] | None,
    ) -> bool:
        if filters is None:
            return True

        if isinstance(filters, dict):
            return all(document.get(field) == value for field, value in filters.items())

        for field, operator, value in filters:
            if operator != "==":
                raise NotImplementedError("MockFirestoreService only supports == filters.")
            if document.get(field) != value:
                return False
        return True

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)
