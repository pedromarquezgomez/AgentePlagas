import logging
from uuid import uuid4
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

from app.audit.contracts import AuditEvent, AuditEventType
from app.audit.service import AuditService, default_audit_service
from app.incidents.sla.contracts import SLAStatus
from app.incidents.sla.engine import SLAEngine
from app.schemas.incident import Incident, IncidentDraft, IncidentRead
from app.services.firestore_factory import get_firestore_service


class IncidentNotFoundError(LookupError):
    pass


class IncidentService:
    def __init__(
        self,
        firestore_service=None,
        audit_service: AuditService | None = None,
        sla_engine: SLAEngine | None = None,
    ) -> None:
        self.firestore_service = firestore_service or get_firestore_service()
        self.audit_service = audit_service or default_audit_service()
        self.sla_engine = sla_engine or SLAEngine()

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
        sla_status: str | None = None,
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
        queue_map = await self._get_global_queue_map()
        read_models = []
        for record in records:
            read_model = self._to_read_model(record, queue_map)
            await self._record_sla_breach_once(record, read_model)
            read_models.append(read_model.model_dump(mode="json"))
        read_models = self._filter_operational_incidents(
            read_models,
            priority=priority,
            pest_type=pest_type,
            dispatch_bucket=dispatch_bucket,
            sla_status=sla_status,
        )
        read_models = self._sort_incidents(read_models, sort_by=sort_by, sort_dir=sort_dir)
        return read_models[:limit] if limit is not None else read_models

    async def get_incident(self, incident_id: str) -> dict:
        incident = await self.firestore_service.get_document("incidents", incident_id)
        if incident is None:
            raise IncidentNotFoundError(f"Incident not found: {incident_id}")
        queue_map = await self._get_global_queue_map()
        read_model = self._to_read_model(incident, queue_map)
        await self._record_sla_breach_once(incident, read_model)
        return read_model.model_dump(mode="json")

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

        old_status = current_incident.get("status")
        new_status = updated_incident.get("status")
        if new_status == "cancelled" and old_status != "cancelled":
            await self._notify_client_incident_cancelled(updated_incident)

        queue_map = await self._get_global_queue_map()
        read_model = self._to_read_model(updated_incident, queue_map)
        await self._record_sla_breach_once(updated_incident, read_model)
        return read_model.model_dump(mode="json")

    def _to_read_model(
        self,
        record: dict,
        queue_map: dict[str, tuple[int, float, str]] | None = None,
    ) -> IncidentRead:
        metadata = record.get("metadata") if isinstance(record.get("metadata"), dict) else {}
        classification = (
            metadata.get("classification")
            if isinstance(metadata.get("classification"), dict)
            else {}
        )
        sla_hours = record.get("sla_hours") or metadata.get("sla_hours")
        sla_assessment = self.sla_engine.assess(
            incident_id=record.get("id"),
            incident_created_at=self._parse_datetime(record.get("created_at")),
            incident_status=record.get("status", "pending_review"),
            sla_hours=self._numeric_hours(sla_hours),
        )
        operational_priority = (
            record.get("operational_priority")
            or metadata.get("operational_priority")
            or self._normalized_operational_priority(metadata.get("priority"))
        )

        incident_id = record.get("id")
        queue_position, queue_score, queue_reason = None, None, None
        if queue_map and incident_id in queue_map:
            queue_position, queue_score, queue_reason = queue_map[incident_id]

        return IncidentRead(
            id=incident_id,
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
            sla_hours=sla_hours,
            sla_status=sla_assessment.sla_status.value,
            elapsed_hours=self._rounded_hours(sla_assessment.elapsed_hours),
            remaining_hours=self._rounded_hours(sla_assessment.remaining_hours),
            breach_hours=self._rounded_hours(sla_assessment.breach_hours),
            created_at=record.get("created_at"),
            updated_at=record.get("updated_at"),
            metadata=metadata,
            queue_position=queue_position,
            queue_score=queue_score,
            queue_reason=queue_reason,
        )

    def _filter_operational_incidents(
        self,
        incidents: list[dict],
        *,
        priority: str | None,
        pest_type: str | None,
        dispatch_bucket: str | None,
        sla_status: str | None,
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
        if sla_status:
            filtered = [
                incident
                for incident in filtered
                if incident.get("sla_status") == sla_status
            ]
        return filtered

    def _sort_incidents(
        self,
        incidents: list[dict],
        *,
        sort_by: str | None,
        sort_dir: str | None,
    ) -> list[dict]:
        effective_sort_by = sort_by
        if not effective_sort_by:
            effective_sort_by = "queue_position"

        if effective_sort_by not in {
            "priority",
            "severity",
            "sla_hours",
            "remaining_hours",
            "breach_hours",
            "sla_status",
            "created_at",
            "queue_position",
        }:
            return incidents

        reverse = sort_dir == "desc"
        priority_order = {"URGENT": 0, "HIGH": 1, "NORMAL": 2, "LOW": 3}
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        sla_status_order = {"BREACHED": 0, "AT_RISK": 1, "ON_TRACK": 2, "COMPLETED": 3}

        def sort_key(incident: dict):
            if effective_sort_by == "queue_position":
                val = incident.get("queue_position")
                if val is None:
                    # Mandar los elementos inactivos (None) al final del orden
                    return 999999 if not reverse else -999999
                return val
            if effective_sort_by == "priority":
                return priority_order.get(incident.get("operational_priority"), 99)
            if effective_sort_by == "severity":
                return severity_order.get(incident.get("severity"), 99)
            if effective_sort_by == "sla_hours":
                value = incident.get("sla_hours")
                return value if isinstance(value, (int, float)) else 999999
            if effective_sort_by == "remaining_hours":
                value = incident.get("remaining_hours")
                return value if isinstance(value, (int, float)) else 999999
            if effective_sort_by == "breach_hours":
                value = incident.get("breach_hours")
                return value if isinstance(value, (int, float)) else 0
            if effective_sort_by == "sla_status":
                return sla_status_order.get(incident.get("sla_status"), 99)
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

    async def _record_sla_breach_once(self, record: dict, read_model: IncidentRead) -> None:
        if read_model.sla_status != SLAStatus.BREACHED.value:
            return
        metadata = record.get("metadata") if isinstance(record.get("metadata"), dict) else {}
        if metadata.get("sla_breach_audited") is True:
            return

        self.audit_service.record_event(
            AuditEvent(
                event_type=AuditEventType.INCIDENT_SLA_BREACHED,
                execution_id=read_model.id,
                user_id=(read_model.conversation_id or "").split(":", 1)[1]
                if read_model.conversation_id and ":" in read_model.conversation_id
                else None,
                channel=read_model.channel,
                status=read_model.sla_status,
                message="Incident SLA breached.",
                metadata={
                    "incident_id": read_model.id,
                    "sla_hours": read_model.sla_hours,
                    "elapsed_hours": read_model.elapsed_hours,
                    "breach_hours": read_model.breach_hours,
                },
            )
        )
        updated_metadata = {
            **metadata,
            "sla_breach_audited": True,
        }
        if read_model.id:
            await self.firestore_service.update_document(
                "incidents",
                read_model.id,
                {"metadata": updated_metadata},
            )

    def _parse_datetime(self, value: object) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return datetime.now(timezone.utc)
        return datetime.now(timezone.utc)

    def _numeric_hours(self, value: object) -> float | None:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return None
        return None

    def _rounded_hours(self, value: float | None) -> float | None:
        if value is None:
            return None
        return round(value, 2)

    async def _get_global_queue_map(self) -> dict[str, tuple[int, float, str]]:
        all_records = await self.firestore_service.list_documents("incidents")
        return await self._calculate_work_queue(all_records)

    async def _calculate_work_queue(self, records: list[dict]) -> dict[str, tuple[int, float, str]]:
        from app.incidents.work_queue.engine import WorkQueueEngine

        active_incidents_data = []
        for record in records:
            status = record.get("status", "pending_review")
            # Excluir completados, cerrados y cancelados de la cola operativa activa
            if status in {"completed", "closed", "cancelled"}:
                continue

            incident_id = record.get("id")
            if not incident_id:
                continue

            sla_hours = record.get("sla_hours") or (record.get("metadata") or {}).get("sla_hours")
            sla_assessment = self.sla_engine.assess(
                incident_id=incident_id,
                incident_created_at=self._parse_datetime(record.get("created_at")),
                incident_status=status,
                sla_hours=self._numeric_hours(sla_hours),
            )
            sla_status = sla_assessment.sla_status.value

            metadata = record.get("metadata") if isinstance(record.get("metadata"), dict) else {}
            operational_priority = (
                record.get("operational_priority")
                or metadata.get("operational_priority")
                or self._normalized_operational_priority(metadata.get("priority"))
                or record.get("priority", "medium")
            )

            severity = record.get("severity") or metadata.get("severity")
            dispatch_bucket = record.get("dispatch_bucket") or metadata.get("dispatch_bucket")
            created_at = record.get("created_at")

            score_data = WorkQueueEngine.rank(
                prioridad=operational_priority,
                severidad=severity,
                dispatch_bucket=dispatch_bucket,
                sla_status=sla_status,
                created_at=created_at,
            )

            active_incidents_data.append({
                "id": incident_id,
                "score": score_data.score,
                "reason": score_data.reason,
            })

        # Ordenar por score descendente
        active_incidents_data.sort(key=lambda x: x["score"], reverse=True)

        positions_map = {}
        for index, item in enumerate(active_incidents_data):
            positions_map[item["id"]] = (index + 1, item["score"], item["reason"])

        return positions_map

    async def _notify_client_incident_cancelled(self, incident: dict) -> None:
        channel = incident.get("channel")
        conversation_id = incident.get("conversation_id")
        if not channel or not conversation_id:
            return

        # Obtener conversación para obtener external_chat_id
        conversation = await self.firestore_service.get_document("conversations", conversation_id)
        external_chat_id = None
        if conversation:
            external_chat_id = conversation.get("external_chat_id")
        if not external_chat_id and ":" in conversation_id:
            external_chat_id = conversation_id.split(":", 1)[1]

        if not external_chat_id:
            return

        pest_type = incident.get("pest_type") or "plagas"
        # Traducir o formatear un poco la plaga para el mensaje
        pest_spanish_map = {
            "COCKROACH": "cucarachas",
            "RODENT": "roedores",
            "ANT": "hormigas",
            "FLYING_INSECT": "insectos voladores",
            "STORED_PRODUCT_INSECT": "insectos de productos almacenados",
            "UNKNOWN": "plagas no identificadas",
        }
        pest_name = pest_spanish_map.get(str(pest_type).upper(), str(pest_type).lower())

        text_message = (
            f"Hola, tu incidencia para el control de {pest_name} ha sido revisada por nuestro equipo y "
            "ha sido descartada. Si tienes alguna otra consulta o necesitas asistencia con otro tipo de plaga, "
            "no dudes en escribirnos."
        )

        from app.schemas.outgoing_message import OutgoingMessage

        if channel == "telegram":
            from app.adapters.telegram_adapter import TelegramAdapter
            try:
                # Usamos settings de la app
                from app.config.settings import settings
                adapter = TelegramAdapter(settings)
                await adapter.send_message(
                    OutgoingMessage(
                        channel="telegram",
                        external_chat_id=str(external_chat_id),
                        text=text_message,
                    )
                )
            except Exception as exc:
                logger.warning("Failed to send proactive cancellation message via telegram: %s", exc)
        elif channel == "whatsapp":
            from app.adapters.whatsapp_adapter import WhatsAppAdapter
            try:
                from app.config.settings import settings
                adapter = WhatsAppAdapter(settings)
                await adapter.send_message(
                    OutgoingMessage(
                        channel="whatsapp",
                        external_chat_id=str(external_chat_id),
                        text=text_message,
                    )
                )
            except Exception as exc:
                logger.warning("Failed to send proactive cancellation message via whatsapp: %s", exc)
