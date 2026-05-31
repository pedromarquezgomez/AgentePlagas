from uuid import uuid4

from app.schemas.operational_document import (
    OperationalDocument,
    OperationalDocumentCreate,
)
from app.services.firestore_factory import get_firestore_service


class OperationalDocumentNotFoundError(LookupError):
    pass


class OperationalDocumentService:
    collection_name = "operational_documents"

    def __init__(self, firestore_service=None) -> None:
        self.firestore_service = firestore_service or get_firestore_service()

    async def create_document(
        self,
        document_create: OperationalDocumentCreate,
    ) -> OperationalDocument:
        document = OperationalDocument(
            id=str(uuid4()),
            **document_create.model_dump(),
        )
        stored_document = await self.firestore_service.create_document(
            self.collection_name,
            document.model_dump(exclude={"created_at", "updated_at"}),
            document_id=document.id,
        )
        return OperationalDocument.model_validate(stored_document)

    async def list_documents(
        self,
        incident_id: str | None = None,
        visit_id: str | None = None,
        document_type: str | None = None,
        status_filter: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        filters = {}
        if incident_id:
            filters["incident_id"] = incident_id
        if visit_id:
            filters["visit_id"] = visit_id
        if document_type:
            filters["document_type"] = document_type
        if status_filter:
            filters["status"] = status_filter

        return await self.firestore_service.list_documents(
            self.collection_name,
            filters=filters or None,
            limit=limit,
        )

    async def get_document(self, document_id: str) -> dict:
        document = await self.firestore_service.get_document(
            self.collection_name,
            document_id,
        )
        if document is None:
            raise OperationalDocumentNotFoundError(
                f"Operational document not found: {document_id}"
            )
        return document

    async def update_document(self, document_id: str, updates: dict) -> dict:
        current_document = await self.firestore_service.get_document(
            self.collection_name,
            document_id,
        )
        if current_document is None:
            raise OperationalDocumentNotFoundError(
                f"Operational document not found: {document_id}"
            )

        await self.firestore_service.update_document(
            self.collection_name,
            document_id,
            updates,
        )

        updated_document = await self.firestore_service.get_document(
            self.collection_name,
            document_id,
        )
        if updated_document is None:
            raise OperationalDocumentNotFoundError(
                f"Operational document not found after update: {document_id}"
            )
        return updated_document
