import logging
from typing import Any

logger = logging.getLogger(__name__)


class IncidentBuilder:
    def __init__(self, firestore_service: Any = None) -> None:
        self.firestore_service = firestore_service

    async def build(
        self,
        conversation_id: str,
        business_context: dict[str, Any] | None = None,
    ) -> tuple[str | None, str | None]:
        # Buscar en Firestore la incidencia activa para la conversación
        if self.firestore_service:
            try:
                docs = await self.firestore_service.list_documents(
                    "incidents",
                    filters={"conversation_id": conversation_id},
                )
                active_incidents = [
                    d for d in docs
                    if d.get("status") not in ("closed", "cancelled")
                ]
                if active_incidents:
                    # Ordenar por created_at de forma descendente para tomar la más reciente
                    sorted_incidents = sorted(
                        active_incidents,
                        key=lambda x: str(x.get("created_at") or ""),
                        reverse=True,
                    )
                    active = sorted_incidents[0]
                    return active.get("id"), active.get("summary")
                elif docs:
                    # Si no hay activos, tomar el más reciente histórico
                    sorted_docs = sorted(
                        docs,
                        key=lambda x: str(x.get("created_at") or ""),
                        reverse=True,
                    )
                    recent = sorted_docs[0]
                    recent_status = recent.get("status", "pending_review")
                    if recent_status in ("closed", "cancelled"):
                        special_summary = f"[ESTADO: DESCARTADO/CANCELADO] {recent.get('summary')}"
                        return recent.get("id"), special_summary
            except Exception as exc:
                logger.warning(
                    "incident_builder_failed conversation_id=%s error=%s",
                    conversation_id,
                    str(exc),
                )

        # Fallback a metadatos de contexto de negocio si están definidos
        if business_context:
            incident_id = business_context.get("incident_id")
            incident_summary = business_context.get("incident_summary")
            if incident_id:
                return incident_id, incident_summary

        return None, None
