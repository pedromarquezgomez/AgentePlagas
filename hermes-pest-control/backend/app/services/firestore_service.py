from copy import deepcopy
from typing import Any
from uuid import uuid4


class FirestoreService:
    def __init__(self) -> None:
        self._collections: dict[str, dict[str, dict[str, Any]]] = {}

    async def create_document(self, collection: str, data: dict[str, Any]) -> dict[str, Any]:
        document_id = str(data.get("id") or uuid4())
        document = deepcopy(data)
        document["id"] = document_id

        self._collections.setdefault(collection, {})[document_id] = document
        return document

    async def get_document(
        self,
        collection: str,
        document_id: str,
    ) -> dict[str, Any] | None:
        document = self._collections.get(collection, {}).get(document_id)
        return deepcopy(document) if document is not None else None

    async def update_document(
        self,
        collection: str,
        document_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        current = self._collections.setdefault(collection, {}).get(document_id, {})
        updated = {**current, **deepcopy(data), "id": document_id}
        self._collections[collection][document_id] = updated
        return updated

