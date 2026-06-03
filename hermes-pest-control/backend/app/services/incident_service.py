from uuid import uuid4

from app.schemas.incident import Incident, IncidentDraft, IncidentRead
from app.services.firestore_factory import get_firestore_service


class IncidentNotFoundError(LookupError):
    pass


class IncidentService:
    def __init__(self, firestore_service=None) -> None:
        self.firestore_service = firestore_service or get_firestore_service()

    async def create_incident(self, incident_draft: IncidentDraft) -> Incident:
        incident = Incident(
            id=str(uuid4()),
            conversation_id=incident_draft.conversation_id,
            channel=incident_draft.channel,
            pest_type=incident_draft.pest_type,
            location=incident_draft.location,
            affected_area=incident_draft.affected_area,
            priority=incident_draft.priority,
            status="pending_review",
            summary=incident_draft.summary,
            confidence=incident_draft.confidence,
            severity=incident_draft.severity,
            operational_priority=incident_draft.operational_priority,
            response_hours=incident_draft.response_hours,
            assessment_reason=incident_draft.assessment_reason,
            visit_type=incident_draft.visit_type,
            technician_level=incident_draft.technician_level,
            dispatch_bucket=incident_draft.dispatch_bucket,
            sla_hours=incident_draft.sla_hours,
            metadata=incident_draft.metadata,
        )
        stored_incident = await self.firestore_service.create_document(
            "incidents",
            incident.model_dump(),
            document_id=incident.id,
        )
        incident.id = stored_incident["id"]
        return incident

    async def list_incidents(
        self,
        status_filter: str | None = None,
        priority: str | None = None,
        pest_type: str | None = None,
        dispatch_bucket: str | None = None,
        sort_by: str | None = None,
        sort_dir: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        filters = {}
        if status_filter:
            filters["status"] = status_filter
        if priority and priority.islower():
            filters["priority"] = priority

        records = await self.firestore_service.list_documents(
            "incidents",
            filters=filters or None,
        )
        read_models = [self._to_read_model(record).model_dump(mode="json") for record in records]
        read_models = self._filter_operational_incidents(
            read_models,
            priority=priority,
            pest_type=pest_type,
            dispatch_bucket=dispatch_bucket,
        )
        read_models = self._sort_incidents(read_models, sort_by=sort_by, sort_dir=sort_dir)
        return read_models[:limit] if limit is not None else read_models

    async def get_incident(self, incident_id: str) -> dict:
        incident = await self.firestore_service.get_document("incidents", incident_id)
        if incident is None:
            raise IncidentNotFoundError(f"Incident not found: {incident_id}")
        return self._to_read_model(incident).model_dump(mode="json")

    async def update_incident(
        self,
        incident_id: str,
        updates: dict,
    ) -> dict:
        current_incident = await self.firestore_service.get_document(
            "incidents",
            incident_id,
        )
        if current_incident is None:
            raise IncidentNotFoundError(f"Incident not found: {incident_id}")

        await self.firestore_service.update_document(
            "incidents",
            incident_id,
            updates,
        )

        updated_incident = await self.firestore_service.get_document(
            "incidents",
            incident_id,
        )
        if updated_incident is None:
            raise IncidentNotFoundError(f"Incident not found after update: {incident_id}")
        return self._to_read_model(updated_incident).model_dump(mode="json")

    def _to_read_model(self, record: dict) -> IncidentRead:
        metadata = record.get("metadata") if isinstance(record.get("metadata"), dict) else {}
        classification = (
            metadata.get("classification")
            if isinstance(metadata.get("classification"), dict)
            else {}
        )
        operational_priority = (
            record.get("operational_priority")
            or metadata.get("operational_priority")
            or self._normalized_operational_priority(metadata.get("priority"))
        )
        return IncidentRead(
            id=record.get("id"),
            conversation_id=record.get("conversation_id"),
            channel=record.get("channel", "telegram"),
            pest_type=record.get("pest_type") or classification.get("pest_type"),
            location=record.get("location"),
            affected_area=record.get("affected_area"),
            priority=record.get("priority", "medium"),
            operational_priority=operational_priority,
            status=record.get("status", "pending_review"),
            summary=record.get("summary"),
            internal_notes=record.get("internal_notes"),
            confidence=record.get("confidence") or metadata.get("confidence") or classification.get("confidence"),
            severity=record.get("severity") or metadata.get("severity"),
            response_hours=record.get("response_hours") or metadata.get("response_hours"),
            assessment_reason=record.get("assessment_reason") or metadata.get("assessment_reason"),
            visit_type=record.get("visit_type") or metadata.get("visit_type"),
            technician_level=record.get("technician_level") or metadata.get("technician_level"),
            dispatch_bucket=record.get("dispatch_bucket") or metadata.get("dispatch_bucket"),
            sla_hours=record.get("sla_hours") or metadata.get("sla_hours"),
            created_at=record.get("created_at"),
            updated_at=record.get("updated_at"),
            metadata=metadata,
        )

    def _filter_operational_incidents(
        self,
        incidents: list[dict],
        *,
        priority: str | None,
        pest_type: str | None,
        dispatch_bucket: str | None,
    ) -> list[dict]:
        filtered = incidents
        if priority and priority.isupper():
            filtered = [
                incident
                for incident in filtered
                if incident.get("operational_priority") == priority
            ]
        if pest_type:
            filtered = [
                incident
                for incident in filtered
                if (incident.get("pest_type") or "").upper() == pest_type.upper()
            ]
        if dispatch_bucket:
            filtered = [
                incident
                for incident in filtered
                if incident.get("dispatch_bucket") == dispatch_bucket
            ]
        return filtered

    def _sort_incidents(
        self,
        incidents: list[dict],
        *,
        sort_by: str | None,
        sort_dir: str | None,
    ) -> list[dict]:
        if sort_by not in {"priority", "severity", "sla_hours", "created_at"}:
            return incidents

        reverse = sort_dir == "desc"
        priority_order = {"URGENT": 0, "HIGH": 1, "NORMAL": 2, "LOW": 3}
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}

        def sort_key(incident: dict):
            if sort_by == "priority":
                return priority_order.get(incident.get("operational_priority"), 99)
            if sort_by == "severity":
                return severity_order.get(incident.get("severity"), 99)
            if sort_by == "sla_hours":
                value = incident.get("sla_hours")
                return value if isinstance(value, int) else 999999
            return str(incident.get("created_at") or "")

        return sorted(incidents, key=sort_key, reverse=reverse)

    def _normalized_operational_priority(self, value: object) -> str | None:
        if not isinstance(value, str) or not value:
            return None
        upper_value = value.upper()
        if upper_value in {"URGENT", "HIGH", "NORMAL", "LOW"}:
            return upper_value
        legacy_map = {
            "urgent": "URGENT",
            "high": "HIGH",
            "medium": "NORMAL",
            "low": "LOW",
        }
        return legacy_map.get(value)
