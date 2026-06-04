from uuid import uuid4
from datetime import datetime, timezone
from app.schemas.operational_document import (
    OperationalDocument,
    OperationalDocumentCreate,
)
from app.schemas.document_version import (
    OperationalDocumentVersion,
    OperationalDocumentVersionCreate,
)
from app.services.firestore_factory import get_firestore_service


class OperationalDocumentNotFoundError(LookupError):
    pass


class OperationalDocumentService:
    collection_name = "operational_documents"
    versions_collection = "operational_document_versions"

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

        # También creamos la versión v1 inicial en la colección de versiones
        await self.create_document_version(
            document_id=document.id,
            content=document.content,
            generated_by=document_create.generated_by,
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

    # --- VERSIONS ---
    async def list_document_versions(self, document_id: str) -> list[dict]:
        # Validamos que el documento exista
        await self.get_document(document_id)

        versions = await self.firestore_service.list_documents(
            self.versions_collection,
            filters={"document_id": document_id},
        )
        # Ordenar por número de versión
        versions.sort(key=lambda x: x.get("version_number", 0))
        return versions

    async def create_document_version(
        self,
        document_id: str,
        content: str,
        generated_by: str = "admin",
    ) -> dict:
        # Obtenemos las versiones existentes para calcular el siguiente número
        existing = await self.firestore_service.list_documents(
            self.versions_collection,
            filters={"document_id": document_id},
        )
        next_ver = len(existing) + 1

        version_data = {
            "id": str(uuid4()),
            "document_id": document_id,
            "version_number": next_ver,
            "content": content,
            "generated_by": generated_by,
        }

        stored = await self.firestore_service.create_document(
            self.versions_collection,
            version_data,
            document_id=version_data["id"],
        )

        # Si no es la primera versión, actualizamos también el contenido del documento principal
        if next_ver > 1:
            await self.firestore_service.update_document(
                self.collection_name,
                document_id,
                {"content": content},
            )

        return stored
