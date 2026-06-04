from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.config.settings import Settings
from app.schemas.incoming_message import IncomingMessage
from app.services.conversation_service import ConversationService
from app.services.mock_firestore_service import MockFirestoreService
from app.audit.service import default_audit_service

DEFAULT_CASES_DIR = Path(__file__).resolve().parent / "cases_multiturn"
DEFAULT_RESULTS_DIR = Path(__file__).resolve().parent / "results"


@dataclass
class TurnEvaluation:
    user_message: str
    expected_action_type: str | None = None
    expected_missing_fields: list[str] | None = None
    expected_bot_contains: list[str] = field(default_factory=list)
    expected_bot_not_contains: list[str] = field(default_factory=list)
    simulate_backend_action: str | None = None
    asserts: dict[str, Any] = field(default_factory=dict)


@dataclass
class MultiTurnCase:
    id: str
    description: str
    turns: list[TurnEvaluation]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MultiTurnCase:
        turns = []
        for turn_data in data["turns"]:
            turns.append(
                TurnEvaluation(
                    user_message=turn_data["user_message"],
                    expected_action_type=turn_data.get("expected_action_type"),
                    expected_missing_fields=turn_data.get("expected_missing_fields"),
                    expected_bot_contains=turn_data.get("expected_bot_contains", []),
                    expected_bot_not_contains=turn_data.get("expected_bot_not_contains", []),
                    simulate_backend_action=turn_data.get("simulate_backend_action"),
                    asserts=turn_data.get("asserts", {}),
                )
            )
        return cls(
            id=data["id"],
            description=data.get("description", ""),
            turns=turns,
        )


async def run_single_case(
    case: MultiTurnCase,
    hermes_mode: str,
) -> tuple[bool, list[str], list[str], list[dict[str, Any]]]:
    """Runs a single multi-turn test case and returns (passed, failure_reasons, transcript, turn_results)."""
    failure_reasons = []
    transcript = []
    turn_results = []

    # Initialize isolated services for this case run
    firestore_service = MockFirestoreService()
    settings = Settings(hermes_mode=hermes_mode, APP_ENV="test")
    conversation_service = ConversationService(
        firestore_service=firestore_service,
        settings=settings,
    )

    external_user_id = f"eval-user-{case.id}"
    external_chat_id = f"eval-chat-{case.id}"
    conversation_id = f"telegram:{external_user_id}"

    transcript.append(f"--- Caso: {case.id} ({case.description}) ---")

    # Clear previous audit events for this test user
    audit_service = default_audit_service()

    for i, turn in enumerate(case.turns):
        turn_failed = False
        turn_reasons = []

        # 1. Execute simulate_backend_action if needed
        if turn.simulate_backend_action:
            if turn.simulate_backend_action == "cancel_incident":
                # Find the incident in Firestore and cancel it
                incidents = await firestore_service.list_documents(
                    "incidents",
                    filters={"conversation_id": conversation_id},
                )
                if incidents:
                    for inc in incidents:
                        await firestore_service.update_document(
                            "incidents",
                            inc["id"],
                            {"status": "cancelled"},
                        )
                    transcript.append(f"[BACKEND SIMULADO] Incidencia(s) marcada(s) como 'cancelled'")
                else:
                    turn_reasons.append(
                        f"simulate_backend_action 'cancel_incident' failed because no incident was found."
                    )

        # 2. Build incoming message
        message = IncomingMessage(
            channel="telegram",
            external_user_id=external_user_id,
            external_chat_id=external_chat_id,
            message_type="text",
            text=turn.user_message,
        )

        transcript.append(f"Usuario: {turn.user_message}")

        # 3. Process message
        bot_reply = ""
        action_type = None
        missing_fields = None
        try:
            response = await conversation_service.handle_incoming_message(message)
            bot_reply = response.reply
            action_type = response.action.type
            missing_fields = response.action.missing_fields
            transcript.append(f"Bot: {bot_reply}")
        except Exception as exc:
            err_msg = f"failed with exception: {exc}"
            turn_reasons.append(err_msg)
            transcript.append(f"Bot Error: {exc}")
            turn_failed = True

        if not turn_failed:
            # 4. Action Type assertions
            if turn.expected_action_type is not None:
                if action_type != turn.expected_action_type:
                    turn_reasons.append(
                        f"expected action_type={turn.expected_action_type!r}, got {action_type!r}"
                    )

            if turn.expected_missing_fields is not None:
                if sorted(missing_fields or []) != sorted(turn.expected_missing_fields):
                    turn_reasons.append(
                        f"expected missing_fields={turn.expected_missing_fields!r}, got {missing_fields!r}"
                    )

            # 5. Text assertions
            bot_reply_lower = bot_reply.casefold()
            for text in turn.expected_bot_contains:
                if text.casefold() not in bot_reply_lower:
                    turn_reasons.append(
                        f"expected bot reply to contain {text!r}"
                    )

            for text in turn.expected_bot_not_contains:
                if text.casefold() in bot_reply_lower:
                    turn_reasons.append(
                        f"expected bot reply NOT to contain {text!r}"
                    )

            # 6. Database assertions
            asserts = turn.asserts
            if asserts:
                incidents = await firestore_service.list_documents(
                    "incidents",
                    filters={"conversation_id": conversation_id},
                )
                has_incident = len(incidents) > 0
                latest_incident = incidents[0] if has_incident else None

                if "incident_created" in asserts:
                    expected_created = asserts["incident_created"]
                    if expected_created != has_incident:
                        turn_reasons.append(
                            f"DB: expected incident_created={expected_created}, got {has_incident}"
                        )

                if latest_incident:
                    if "incident_pest_type" in asserts:
                        expected_pest = asserts["incident_pest_type"]
                        actual_pest = latest_incident.get("pest_type")
                        if expected_pest != actual_pest:
                            turn_reasons.append(
                                f"DB: expected pest_type={expected_pest!r}, got {actual_pest!r}"
                            )
                    if "incident_location" in asserts:
                        expected_loc = asserts["incident_location"]
                        actual_loc = latest_incident.get("location")
                        if expected_loc != actual_loc:
                            turn_reasons.append(
                                f"DB: expected location={expected_loc!r}, got {actual_loc!r}"
                            )
                    if "incident_affected_area" in asserts:
                        expected_area = asserts["incident_affected_area"]
                        actual_area = latest_incident.get("affected_area")
                        if expected_area != actual_area:
                            turn_reasons.append(
                                f"DB: expected affected_area={expected_area!r}, got {actual_area!r}"
                            )
                    if "incident_status" in asserts:
                        expected_status = asserts["incident_status"]
                        actual_status = latest_incident.get("status")
                        if expected_status != actual_status:
                            turn_reasons.append(
                                f"DB: expected status={expected_status!r}, got {actual_status!r}"
                            )

                if "tool_proposed" in asserts:
                    expected_tool = asserts["tool_proposed"]
                    records = await firestore_service.list_documents("tool_execution_records")
                    conv_records = [
                        r for r in records
                        if r.get("conversation_id") == conversation_id and r.get("tool_name") == expected_tool
                    ]
                    has_record = len(conv_records) > 0
                    if not has_record:
                        turn_reasons.append(
                            f"DB: expected tool {expected_tool!r} to be proposed, but it was not."
                        )

                if "visit_slot_selected" in asserts:
                    expected_slot_idx = asserts["visit_slot_selected"]
                    records = await firestore_service.list_documents("tool_execution_records")
                    conv_records = [
                        r for r in records
                        if r.get("conversation_id") == conversation_id and r.get("tool_name") == "schedule_visit_tool"
                    ]
                    if conv_records:
                        payload = conv_records[0].get("approved_payload") or {}
                        sel_slot = payload.get("selected_slot") or {}
                        actual_idx = sel_slot.get("slot_index")
                        if actual_idx != expected_slot_idx:
                            turn_reasons.append(
                                f"DB: expected selected slot_index={expected_slot_idx}, got {actual_idx}"
                            )
                    else:
                        turn_reasons.append(
                            "DB: expected visit slot selection, but no schedule_visit_tool record was found."
                        )

                # 7. Audit assertions
                if "audit_events" in asserts:
                    expected_events = asserts["audit_events"]
                    all_events = audit_service.list_events()
                    user_events = [e for e in all_events if e.user_id == external_user_id]
                    recorded_types = [e.event_type for e in user_events]
                    for ev_type in expected_events:
                        if ev_type not in recorded_types:
                            turn_reasons.append(
                                f"Audit: expected event type {ev_type!r} to be recorded, but it was not. Recorded: {recorded_types}"
                            )

        # Record result for this turn
        turn_passed = len(turn_reasons) == 0
        turn_results.append({
            "turn_index": i + 1,
            "user_message": turn.user_message,
            "bot_reply": bot_reply,
            "passed": turn_passed,
            "reasons": turn_reasons,
        })

        if not turn_passed:
            failure_reasons.extend([f"Turn {i+1}: {r}" for r in turn_reasons])

    passed = len(failure_reasons) == 0
    return passed, failure_reasons, transcript, turn_results


def load_multi_turn_cases(cases_dir: Path) -> list[MultiTurnCase]:
    cases = []
    for file_path in sorted(cases_dir.glob("*.json")):
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if "cases" in data:
            for case_data in data["cases"]:
                cases.append(MultiTurnCase.from_dict(case_data))
        else:
            cases.append(MultiTurnCase.from_dict(data))
    return cases


def generate_markdown_report(
    results_list: list[dict[str, Any]],
    hermes_mode: str,
    passed_count: int,
    failed_count: int,
) -> str:
    md = []
    md.append(f"# Reporte de Pruebas Conversacionales Multi-Turno ({hermes_mode})")
    md.append("")
    md.append(f"**Resultado:** {'🟢 PASÓ' if failed_count == 0 else '🔴 FALLÓ'}")
    md.append(f"- **Casos totales:** {passed_count + failed_count}")
    md.append(f"- **Pasados:** {passed_count}")
    md.append(f"- **Fallados:** {failed_count}")
    md.append("")
    md.append("## Detalle de Casos")
    md.append("")

    for case in results_list:
        status_emoji = "🟢" if case["passed"] else "🔴"
        md.append(f"### {status_emoji} Case ID: `{case['id']}`")
        md.append(f"*{case['description']}*")
        md.append("")
        md.append("#### Transcripción:")
        md.append("```text")
        md.append("\n".join(case["transcript"]))
        md.append("```")
        md.append("")
        if not case["passed"]:
            md.append("#### Errores encontrados:")
            for reason in case["reasons"]:
                md.append(f"- {reason}")
            md.append("")
        md.append("---")
        md.append("")

    return "\n".join(md)


async def run_all_evals(cases_dir: Path, hermes_mode: str, results_dir: Path) -> int:
    cases = load_multi_turn_cases(cases_dir)
    print(f"Cargados {len(cases)} casos multi-turno de {cases_dir}")

    passed_count = 0
    failed_count = 0
    results_list = []

    for case in cases:
        passed, reasons, transcript, turns = await run_single_case(case, hermes_mode)
        print("\n".join(transcript))
        if passed:
            print(f"\033[92m[PASS] {case.id}\033[0m")
            passed_count += 1
        else:
            print(f"\033[91m[FAIL] {case.id}\033[0m")
            for r in reasons:
                print(f"  - {r}")
            failed_count += 1
        print("=" * 60)

        results_list.append({
            "id": case.id,
            "description": case.description,
            "passed": passed,
            "reasons": reasons,
            "transcript": transcript,
            "turns": turns,
        })

    print("\nResumen Evaluaciones Multi-Turno:")
    print(f"  Total:  {len(cases)}")
    print(f"  Pasados: \033[92m{passed_count}\033[0m")
    print(f"  Fallados: \033[91m{failed_count}\033[0m")

    # Export results to JSON
    results_dir.mkdir(parents=True, exist_ok=True)
    json_path = results_dir / "multiturn_latest.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump({
            "hermes_mode": hermes_mode,
            "passed": passed_count,
            "failed": failed_count,
            "results": results_list,
        }, f, ensure_ascii=False, indent=2)
    print(f"Resultados JSON exportados a: {json_path}")

    # Export results to Markdown
    md_path = results_dir / "multiturn_latest.md"
    md_content = generate_markdown_report(results_list, hermes_mode, passed_count, failed_count)
    with md_path.open("w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"Reporte Markdown exportado a: {md_path}")

    return 0 if failed_count == 0 else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Run multi-turn conversation evaluations.")
    parser.add_argument(
        "--cases-dir",
        type=Path,
        default=DEFAULT_CASES_DIR,
        help="Directory containing JSON cases.",
    )
    parser.add_argument(
        "--hermes-mode",
        choices=["mock", "real"],
        default="mock",
        help="Hermes mode to run. Defaults to mock.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=DEFAULT_RESULTS_DIR,
        help="Directory to write output results.",
    )
    args = parser.parse_args()

    exit_code = asyncio.run(run_all_evals(args.cases_dir, args.hermes_mode, args.results_dir))
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
