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

DEFAULT_CASES_DIR = Path(__file__).resolve().parent / "cases_multiturn"


@dataclass
class TurnEvaluation:
    user_message: str
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
) -> tuple[bool, list[str], list[str]]:
    """Runs a single multi-turn test case and returns (passed, failure_reasons, transcript)."""
    failure_reasons = []
    transcript = []

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

    for i, turn in enumerate(case.turns):
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
                    failure_reasons.append(
                        f"Turn {i+1}: simulate_backend_action 'cancel_incident' failed because no incident was found."
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
        try:
            response = await conversation_service.handle_incoming_message(message)
            bot_reply = response.reply
            transcript.append(f"Bot: {bot_reply}")
        except Exception as exc:
            err_msg = f"Turn {i+1} failed with exception: {exc}"
            failure_reasons.append(err_msg)
            transcript.append(f"Bot Error: {exc}")
            break

        # 4. Assertions on response text
        bot_reply_lower = bot_reply.casefold()
        for text in turn.expected_bot_contains:
            if text.casefold() not in bot_reply_lower:
                failure_reasons.append(
                    f"Turn {i+1}: expected bot reply to contain {text!r}, got: {bot_reply!r}"
                )

        for text in turn.expected_bot_not_contains:
            if text.casefold() in bot_reply_lower:
                failure_reasons.append(
                    f"Turn {i+1}: expected bot reply NOT to contain {text!r}, got: {bot_reply!r}"
                )

        # 5. Database assertions
        asserts = turn.asserts
        if not asserts:
            continue

        # Get current state of incidents
        incidents = await firestore_service.list_documents(
            "incidents",
            filters={"conversation_id": conversation_id},
        )
        has_incident = len(incidents) > 0
        latest_incident = incidents[0] if has_incident else None

        if "incident_created" in asserts:
            expected_created = asserts["incident_created"]
            if expected_created != has_incident:
                failure_reasons.append(
                    f"Turn {i+1} DB: expected incident_created={expected_created}, got {has_incident}"
                )

        if latest_incident:
            if "incident_pest_type" in asserts:
                expected_pest = asserts["incident_pest_type"]
                actual_pest = latest_incident.get("pest_type")
                if expected_pest != actual_pest:
                    failure_reasons.append(
                        f"Turn {i+1} DB: expected pest_type={expected_pest!r}, got {actual_pest!r}"
                    )
            if "incident_location" in asserts:
                expected_loc = asserts["incident_location"]
                actual_loc = latest_incident.get("location")
                if expected_loc != actual_loc:
                    failure_reasons.append(
                        f"Turn {i+1} DB: expected location={expected_loc!r}, got {actual_loc!r}"
                    )
            if "incident_affected_area" in asserts:
                expected_area = asserts["incident_affected_area"]
                actual_area = latest_incident.get("affected_area")
                if expected_area != actual_area:
                    failure_reasons.append(
                        f"Turn {i+1} DB: expected affected_area={expected_area!r}, got {actual_area!r}"
                    )
            if "incident_status" in asserts:
                expected_status = asserts["incident_status"]
                actual_status = latest_incident.get("status")
                if expected_status != actual_status:
                    failure_reasons.append(
                        f"Turn {i+1} DB: expected status={expected_status!r}, got {actual_status!r}"
                    )

        if "visit_proposed" in asserts:
            expected_proposed = asserts["visit_proposed"]
            # Fetch proposed visit tools from tool_execution_records
            records = await firestore_service.list_documents("tool_execution_records")
            conv_records = [
                r for r in records
                if r.get("conversation_id") == conversation_id and r.get("tool_name") == "schedule_visit_tool"
            ]
            has_record = len(conv_records) > 0
            if expected_proposed != has_record:
                failure_reasons.append(
                    f"Turn {i+1} DB: expected visit_proposed={expected_proposed}, got {has_record}"
                )
            if has_record and "visit_status" in asserts:
                expected_v_status = asserts["visit_status"]
                actual_v_status = conv_records[0].get("review_status")
                if expected_v_status != actual_v_status:
                    failure_reasons.append(
                        f"Turn {i+1} DB: expected visit status={expected_v_status!r}, got {actual_v_status!r}"
                    )

    passed = len(failure_reasons) == 0
    return passed, failure_reasons, transcript


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


async def run_all_evals(cases_dir: Path, hermes_mode: str) -> int:
    cases = load_multi_turn_cases(cases_dir)
    print(f"Cargados {len(cases)} casos multi-turno de {cases_dir}")

    passed_count = 0
    failed_count = 0

    for case in cases:
        passed, reasons, transcript = await run_single_case(case, hermes_mode)
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

    print("\nResumen Evaluaciones Multi-Turno:")
    print(f"  Total:  {len(cases)}")
    print(f"  Pasados: \033[92m{passed_count}\033[0m")
    print(f"  Fallados: \033[91m{failed_count}\033[0m")

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
    args = parser.parse_args()

    exit_code = asyncio.run(run_all_evals(args.cases_dir, args.hermes_mode))
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
