from datetime import datetime, timezone
from uuid import uuid4

from app.schemas.human_review import (
    HumanReviewItem,
    HumanReviewItemCreate,
)
from app.services.firestore_factory import get_firestore_service


class HumanReviewItemNotFoundError(LookupError):
    pass


class HumanReviewService:
    collection_name = "human_review_items"

    def __init__(self, firestore_service=None) -> None:
        self.firestore_service = firestore_service or get_firestore_service()

    async def create_review_item(
        self,
        review_item: HumanReviewItemCreate,
    ) -> HumanReviewItem:
        item = HumanReviewItem(
            id=str(uuid4()),
            status="open",
            **review_item.model_dump(),
        )
        stored_item = await self.firestore_service.create_document(
            self.collection_name,
            item.model_dump(exclude={"created_at", "updated_at", "resolved_at"}),
            document_id=item.id,
        )
        return HumanReviewItem.model_validate(stored_item)

    async def list_review_items(
        self,
        status_filter: str | None = None,
        priority: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        filters = {}
        if status_filter:
            filters["status"] = status_filter
        if priority:
            filters["priority"] = priority

        return await self.firestore_service.list_documents(
            self.collection_name,
            filters=filters or None,
            limit=limit,
        )

    async def get_review_item(self, item_id: str) -> dict:
        item = await self.firestore_service.get_document(self.collection_name, item_id)
        if item is None:
            raise HumanReviewItemNotFoundError(
                f"Human review item not found: {item_id}"
            )
        return item

    async def update_review_item(
        self,
        item_id: str,
        updates: dict,
    ) -> dict:
        current_item = await self.firestore_service.get_document(
            self.collection_name,
            item_id,
        )
        if current_item is None:
            raise HumanReviewItemNotFoundError(
                f"Human review item not found: {item_id}"
            )

        resolved_update = dict(updates)
        if resolved_update.get("status") in {"resolved", "dismissed"}:
            resolved_update["resolved_at"] = datetime.now(timezone.utc)
        elif resolved_update.get("status") in {"open", "in_review"}:
            resolved_update["resolved_at"] = None

        await self.firestore_service.update_document(
            self.collection_name,
            item_id,
            resolved_update,
        )

        updated_item = await self.firestore_service.get_document(
            self.collection_name,
            item_id,
        )
        if updated_item is None:
            raise HumanReviewItemNotFoundError(
                f"Human review item not found after update: {item_id}"
            )
        return updated_item
