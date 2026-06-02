from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config.settings import Settings
from app.schemas.tool_harness import ToolDecision, ToolExecutionRecord, ToolRequest
from app.services.firestore_factory import get_firestore_service
from app.services.mock_firestore_service import MockFirestoreService
from app.services.tool_execution_service import ToolExecutionService
from experiments.nous_hermes_controlled.tool_harness import HermesToolHarness


def build_seed_requests() -> list[ToolRequest]:
    trace_id = "seed-tool-actions"
    conversation_id = "seed:tool-actions"

    return [
        ToolRequest(
            tool_name="gmail.create_draft",
            provider="gmail",
            action="create_draft",
            target={"recipient": "cliente@example.test"},
            payload={
                "subject": "Resumen de visita propuesta",
                "body": "Borrador interno para revisar antes de enviar.",
            },
            risk_level=1,
            requires_approval=False,
            reason="Crear un borrador de email revisable para el operador.",
            trace_id=trace_id,
            conversation_id=conversation_id,
            metadata={"seed_case": "gmail_draft_allowed"},
        ),
        ToolRequest(
            tool_name="gmail.send_email",
            provider="gmail",
            action="send_email",
            target={"recipient": "cliente@example.test"},
            payload={
                "subject": "Resumen de visita",
                "body": "Intento de envio directo bloqueado por politica.",
            },
            risk_level=3,
            requires_approval=True,
            reason="Enviar email directamente no esta permitido en la PoC.",
            trace_id=trace_id,
            conversation_id=conversation_id,
            metadata={"seed_case": "gmail_send_denied"},
        ),
        ToolRequest(
            tool_name="calendar.propose_event",
            provider="calendar",
            action="propose_event",
            target={"calendar": "operaciones"},
            payload={
                "title": "Visita control de cucarachas",
                "location": "Torremolinos",
                "time_window": "manana por la manana",
            },
            risk_level=3,
            requires_approval=True,
            reason="Proponer una visita en calendario para revision humana.",
            trace_id=trace_id,
            conversation_id=conversation_id,
            metadata={"seed_case": "calendar_propose_requires_approval"},
        ),
        ToolRequest(
            tool_name="telegram.draft_message",
            provider="telegram",
            action="draft_message",
            target={"chat_id": "cliente-demo"},
            payload={
                "text": "Borrador: hemos recibido tu solicitud y la revisara el equipo.",
            },
            risk_level=1,
            requires_approval=True,
            reason="Borrador de Telegram para revision, nunca envio directo.",
            trace_id=trace_id,
            conversation_id=conversation_id,
            metadata={"seed_case": "telegram_draft_reviewable"},
        ),
        ToolRequest(
            tool_name="whatsapp.draft_message",
            provider="whatsapp",
            action="draft_message",
            target={"phone": "+34000000000"},
            payload={
                "text": "Indicar al cliente que fumigue con producto quimico.",
            },
            risk_level=5,
            requires_approval=True,
            reason="Consejo quimico peligroso debe bloquearse.",
            trace_id=trace_id,
            conversation_id=conversation_id,
            metadata={"seed_case": "whatsapp_chemical_denied"},
        ),
        ToolRequest(
            tool_name="firestore.direct_write",
            provider="firestore",
            action="direct_write",
            target={"collection": "incidents"},
            payload={
                "summary": "Intento de escritura directa simulado.",
            },
            risk_level=5,
            requires_approval=True,
            reason="Nous Hermes no puede escribir directamente en Firestore.",
            trace_id=trace_id,
            conversation_id=conversation_id,
            metadata={"seed_case": "firestore_direct_write_denied"},
        ),
    ]


def build_seed_records(settings: Settings | None = None) -> list[ToolExecutionRecord]:
    current_settings = settings or _seed_settings()
    harness = HermesToolHarness(settings=current_settings)
    records: list[ToolExecutionRecord] = []
    seed_approved_gmail = os.environ.get("SEED_APPROVED_GMAIL_DRAFT") == "true"

    for request in build_seed_requests():
        decision = _decision_for_seed_case(request, harness)
        record = harness.build_execution_record(request, decision)
        if seed_approved_gmail and request.tool_name == "gmail.create_draft":
            record.review_status = "approved"
            record.reviewer_notes = "Seed aprobado para prueba controlada de Gmail draft."
            record.reviewed_by = "seed_tool_execution_records"
            record.approved_payload = {
                "recipient": os.environ.get(
                    "GMAIL_TEST_DRAFT_RECIPIENT",
                    "cliente@example.test",
                ),
                "subject": "Prueba controlada Hermes Gmail draft",
                "body": (
                    "Borrador de prueba creado desde Acciones IA. "
                    "No enviar este correo."
                ),
            }
        records.append(record)

    return records


async def seed_tool_execution_records(
    service: ToolExecutionService,
    settings: Settings | None = None,
) -> list[ToolExecutionRecord]:
    records = build_seed_records(settings=settings)
    created: list[ToolExecutionRecord] = []
    for record in records:
        created.append(await service.create_execution_record(record))
    return created


async def main() -> int:
    settings = Settings()
    firestore_service = get_firestore_service(settings)
    if not isinstance(firestore_service, MockFirestoreService):
        confirmed = os.environ.get("CONFIRM_SEED_TOOL_RECORDS") == "true"
        if not confirmed:
            print("Tool execution seed aborted.")
            print("Detected real Firestore service.")
            print("Set CONFIRM_SEED_TOOL_RECORDS=true to seed controlled pilot data.")
            return 1

    service = ToolExecutionService(firestore_service)
    created = await seed_tool_execution_records(service, settings=_seed_settings())

    print("Tool execution seed complete")
    print(f"records_created={len(created)}")
    print("external_tools_executed=false")
    for record in created:
        print(
            f"- {record.id} tool_name={record.tool_name} "
            f"decision={record.decision} review_status={record.review_status} "
            f"executed={record.executed}"
        )
    return 0


def _seed_settings() -> Settings:
    return Settings(
        nous_hermes_tools_enabled=True,
        nous_hermes_allowed_tools=(
            "gmail.create_draft,gmail.send_email,calendar.propose_event,"
            "telegram.draft_message,whatsapp.draft_message,firestore.direct_write"
        ),
        tool_harness_enforcement="strict",
    )


def _decision_for_seed_case(
    request: ToolRequest,
    harness: HermesToolHarness,
) -> ToolDecision:
    return harness.decide(request)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
