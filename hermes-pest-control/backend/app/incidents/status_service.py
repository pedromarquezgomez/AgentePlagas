import re
import logging
from typing import Any

logger = logging.getLogger(__name__)


class IncidentStatusService:
    def __init__(self, firestore_service: Any = None) -> None:
        from app.services.firestore_factory import get_firestore_service
        self.firestore_service = firestore_service or get_firestore_service()

    # Patrones para detectar consultas sobre el estado de la incidencia
    status_patterns = [
        r"\bcomo\s+va\b",
        r"\bcómo\s+va\b",
        r"\bestado\b",
        r"\bnovedades\b",
        r"\bhay\s+novedades\b",
        r"\bmi\s+incidencia\b",
        r"\bmi\s+reporte\b",
        r"\bmi\s+aviso\b",
        r"\bqué\s+pasa\s+con\b",
        r"\bque\s+pasa\s+con\b",
    ]

    status_mappings = {
        "pending_review": "Tu incidencia está registrada y pendiente de revisión.",
        "cancelled": "Tu incidencia ha sido descartada/cancelada.",
        "closed": "Tu incidencia ha sido cerrada.",
        "in_progress": "Tu incidencia está en curso.",
    }

    def is_status_query(self, text: str) -> bool:
        if not text:
            return False
        text_lower = text.lower()
        return any(re.search(pattern, text_lower) for pattern in self.status_patterns)

    def get_status_message(self, status: str) -> str:
        return self.status_mappings.get(
            status,
            "Tu incidencia se encuentra registrada y en proceso de gestión."
        )

    async def resolve_status_message(self, conversation_id: str) -> str | None:
        try:
            # Buscar incidencias asociadas a esta conversación
            incidents = await self.firestore_service.list_documents(
                "incidents",
                filters={"conversation_id": conversation_id},
            )
            if not incidents:
                return None
            
            # Ordenar por fecha de creación descendente para tomar la más reciente
            sorted_incidents = sorted(
                incidents,
                key=lambda x: str(x.get("created_at") or ""),
                reverse=True,
            )
            latest_incident = sorted_incidents[0]
            status = latest_incident.get("status", "pending_review")
            return self.get_status_message(status)
        except Exception as exc:
            logger.warning(
                "status_resolution_failed conversation_id=%s error=%s",
                conversation_id,
                exc,
            )
            return None
