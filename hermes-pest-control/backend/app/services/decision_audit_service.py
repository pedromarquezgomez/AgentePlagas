from uuid import uuid4

from app.schemas.decision_record import DecisionRecord, DecisionRecordCreate
from app.services.firestore_factory import get_firestore_service


class DecisionRecordNotFoundError(LookupError):
    pass


class DecisionAuditService:
    collection_name = "decision_records"

    def __init__(self, firestore_service=None) -> None:
        self.firestore_service = firestore_service or get_firestore_service()

    async def create_decision_record(
        self,
        decision_record: DecisionRecordCreate,
    ) -> DecisionRecord:
        record = DecisionRecord(
            id=str(uuid4()),
            **decision_record.model_dump(),
        )
        stored_record = await self.firestore_service.create_document(
            self.collection_name,
            record.model_dump(exclude={"created_at"}),
            document_id=record.id,
        )
        return DecisionRecord.model_validate(stored_record)

    async def get_decision_record(self, decision_record_id: str) -> dict:
        record = await self.firestore_service.get_document(
            self.collection_name,
            decision_record_id,
        )
        if record is None:
            raise DecisionRecordNotFoundError(
                f"Decision record not found: {decision_record_id}"
            )
        return record

    async def list_decision_records(
        self,
        conversation_id: str | None = None,
        action_type: str | None = None,
        fallback_used: bool | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        filters = {}
        if conversation_id:
            filters["conversation_id"] = conversation_id
        if action_type:
            filters["action_type"] = action_type
        if fallback_used is not None:
            filters["fallback_used"] = fallback_used

        return await self.firestore_service.list_documents(
            self.collection_name,
            filters=filters or None,
            limit=limit,
        )
