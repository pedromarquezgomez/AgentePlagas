import re
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.calendar.contracts import SelectedVisitSlot

logger = logging.getLogger(__name__)


class VisitSlotSelectionService:
    def __init__(self, firestore_service: Any = None) -> None:
        from app.services.firestore_factory import get_firestore_service
        self.firestore_service = firestore_service or get_firestore_service()

    first_patterns = [
        r"\bprimera\s+opci[oó]n\b",
        r"\bopci[oó]n\s+1\b",
        r"\bprimer\s+horario\b",
    ]
    second_patterns = [
        r"\bsegunda\s+opci[oó]n\b",
        r"\bopci[oó]n\s+2\b",
        r"\bsegundo\s+horario\b",
    ]
    third_patterns = [
        r"\btercera\s+opci[oó]n\b",
        r"\bopci[oó]n\s+3\b",
        r"\btercer\s+horario\b",
    ]

    def interpret_selection(self, text: str) -> int | None:
        if not text:
            return None
        text_lower = text.lower()

        matches_first = any(re.search(pat, text_lower) for pat in self.first_patterns)
        matches_second = any(re.search(pat, text_lower) for pat in self.second_patterns)
        matches_third = any(re.search(pat, text_lower) for pat in self.third_patterns)

        # Si hay ambigüedad (más de uno coincide), no se puede determinar la opción
        matches_count = sum([matches_first, matches_second, matches_third])
        if matches_count != 1:
            return None

        if matches_first:
            return 1
        if matches_second:
            return 2
        if matches_third:
            return 3

        return None

    async def locate_active_proposal(self, conversation_id: str) -> dict[str, Any] | None:
        try:
            records = await self.firestore_service.list_documents(
                "tool_execution_records",
                filters={
                    "conversation_id": conversation_id,
                    "tool_name": "schedule_visit_tool",
                    "review_status": "proposed",
                }
            )
            if not records:
                return None

            # Ordenar para tomar el más reciente
            sorted_records = sorted(
                records,
                key=lambda x: str(x.get("created_at") or ""),
                reverse=True,
            )
            return sorted_records[0]
        except Exception as exc:
            logger.warning(
                "locate_active_proposal_failed conversation_id=%s error=%s",
                conversation_id,
                exc,
            )
            return None

    async def resolve_selection(self, conversation_id: str, text: str) -> SelectedVisitSlot | None:
        record = await self.locate_active_proposal(conversation_id)
        if not record:
            return None

        payload = record.get("approved_payload") or {}
        proposed_slots = payload.get("proposed_slots") or []
        if not proposed_slots:
            return None

        slot_index = self.interpret_selection(text)
        if slot_index is None:
            return None

        # El slot_index es 1-based. Verificamos que esté en rango de los propuestos
        if slot_index < 1 or slot_index > len(proposed_slots):
            return None

        start_time = proposed_slots[slot_index - 1]
        try:
            # Calcular end_time sumando 60 minutos al start_time (ISO timestamp)
            dt_start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            dt_end = dt_start + timedelta(minutes=60)
            end_time = dt_end.isoformat().replace("+00:00", "Z")
        except Exception as exc:
            logger.warning("failed_to_calculate_end_time start_time=%s error=%s", start_time, exc)
            # Fallback simple
            end_time = start_time

        return SelectedVisitSlot(
            slot_index=slot_index,
            start_time=start_time,
            end_time=end_time,
            selection_text=text,
        )
