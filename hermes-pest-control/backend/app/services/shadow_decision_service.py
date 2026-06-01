from uuid import uuid4

from app.schemas.shadow_decision_record import (
    ShadowDecisionRecord,
    ShadowDecisionRecordCreate,
)
from app.services.firestore_factory import get_firestore_service


class ShadowDecisionRecordNotFoundError(LookupError):
    pass


class ShadowDecisionService:
    collection_name = "shadow_decision_records"

    def __init__(self, firestore_service=None) -> None:
        self.firestore_service = firestore_service or get_firestore_service()

    async def create_shadow_record(
        self,
        shadow_record: ShadowDecisionRecordCreate,
    ) -> ShadowDecisionRecord:
        record = ShadowDecisionRecord(
            id=str(uuid4()),
            **shadow_record.model_dump(),
        )
        stored_record = await self.firestore_service.create_document(
            self.collection_name,
            record.model_dump(exclude={"created_at"}),
            document_id=record.id,
        )
        return ShadowDecisionRecord.model_validate(stored_record)

    async def get_shadow_record(self, shadow_record_id: str) -> dict:
        record = await self.firestore_service.get_document(
            self.collection_name,
            shadow_record_id,
        )
        if record is None:
            raise ShadowDecisionRecordNotFoundError(
                f"Shadow decision record not found: {shadow_record_id}"
            )
        return record

    async def list_shadow_records(
        self,
        conversation_id: str | None = None,
        channel: str | None = None,
        shadow_action_type: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        filters = {}
        if conversation_id:
            filters["conversation_id"] = conversation_id
        if channel:
            filters["channel"] = channel
        if shadow_action_type:
            filters["shadow_action_type"] = shadow_action_type

        return await self.firestore_service.list_documents(
            self.collection_name,
            filters=filters or None,
            limit=limit,
        )
