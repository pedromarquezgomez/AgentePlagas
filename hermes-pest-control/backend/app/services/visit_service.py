from uuid import uuid4
from datetime import date, datetime

from app.schemas.visit import Visit, VisitCreate
from app.services.firestore_factory import get_firestore_service


class VisitNotFoundError(LookupError):
    pass


class VisitService:
    collection_name = "visits"

    def __init__(self, firestore_service=None) -> None:
        self.firestore_service = firestore_service or get_firestore_service()

    async def create_visit(self, visit_create: VisitCreate) -> Visit:
        visit = Visit(
            id=str(uuid4()),
            **visit_create.model_dump(),
        )
        stored_visit = await self.firestore_service.create_document(
            self.collection_name,
            visit.model_dump(exclude={"created_at", "updated_at"}),
            document_id=visit.id,
        )
        return Visit.model_validate(stored_visit)

    async def list_visits(
        self,
        incident_id: str | None = None,
        technician_id: str | None = None,
        status_filter: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        filters = {}
        if incident_id:
            filters["incident_id"] = incident_id
        if technician_id:
            filters["technician_id"] = technician_id
        if status_filter:
            filters["status"] = status_filter

        return await self.firestore_service.list_documents(
            self.collection_name,
            filters=filters or None,
            limit=limit,
        )

    async def list_calendar_visits(
        self,
        start_date: date,
        end_date: date,
        technician_id: str | None = None,
        status_filter: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        visits = await self.list_visits(
            technician_id=technician_id,
            status_filter=status_filter,
            limit=None,
        )
        filtered_visits = [
            visit
            for visit in visits
            if self._is_visit_in_date_range(visit, start_date, end_date)
        ]
        return filtered_visits[:limit] if limit is not None else filtered_visits

    async def get_visit(self, visit_id: str) -> dict:
        visit = await self.firestore_service.get_document(self.collection_name, visit_id)
        if visit is None:
            raise VisitNotFoundError(f"Visit not found: {visit_id}")
        return visit

    async def update_visit(
        self,
        visit_id: str,
        updates: dict,
    ) -> dict:
        current_visit = await self.firestore_service.get_document(
            self.collection_name,
            visit_id,
        )
        if current_visit is None:
            raise VisitNotFoundError(f"Visit not found: {visit_id}")

        await self.firestore_service.update_document(
            self.collection_name,
            visit_id,
            updates,
        )

        updated_visit = await self.firestore_service.get_document(
            self.collection_name,
            visit_id,
        )
        if updated_visit is None:
            raise VisitNotFoundError(f"Visit not found after update: {visit_id}")
        return updated_visit

    def _is_visit_in_date_range(
        self,
        visit: dict,
        start_date: date,
        end_date: date,
    ) -> bool:
        scheduled_start = self._parse_datetime(visit.get("scheduled_start"))
        if scheduled_start is None:
            return False
        scheduled_date = scheduled_start.date()
        return start_date <= scheduled_date <= end_date

    def _parse_datetime(self, value: object) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None
