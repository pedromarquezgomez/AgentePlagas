from uuid import uuid4

from app.schemas.technician import Technician, TechnicianCreate
from app.services.firestore_factory import get_firestore_service


class TechnicianNotFoundError(LookupError):
    pass


class TechnicianService:
    collection_name = "technicians"

    def __init__(self, firestore_service=None) -> None:
        self.firestore_service = firestore_service or get_firestore_service()

    async def create_technician(
        self,
        technician_create: TechnicianCreate,
    ) -> Technician:
        technician = Technician(
            id=str(uuid4()),
            **technician_create.model_dump(),
        )
        stored_technician = await self.firestore_service.create_document(
            self.collection_name,
            technician.model_dump(exclude={"created_at", "updated_at"}),
            document_id=technician.id,
        )
        return Technician.model_validate(stored_technician)

    async def list_technicians(
        self,
        active: bool | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        filters = {}
        if active is not None:
            filters["active"] = active

        return await self.firestore_service.list_documents(
            self.collection_name,
            filters=filters or None,
            limit=limit,
        )

    async def get_technician(self, technician_id: str) -> dict:
        technician = await self.firestore_service.get_document(
            self.collection_name,
            technician_id,
        )
        if technician is None:
            raise TechnicianNotFoundError(f"Technician not found: {technician_id}")
        return technician

    async def update_technician(
        self,
        technician_id: str,
        updates: dict,
    ) -> dict:
        current_technician = await self.firestore_service.get_document(
            self.collection_name,
            technician_id,
        )
        if current_technician is None:
            raise TechnicianNotFoundError(f"Technician not found: {technician_id}")

        await self.firestore_service.update_document(
            self.collection_name,
            technician_id,
            updates,
        )

        updated_technician = await self.firestore_service.get_document(
            self.collection_name,
            technician_id,
        )
        if updated_technician is None:
            raise TechnicianNotFoundError(
                f"Technician not found after update: {technician_id}"
            )
        return updated_technician
