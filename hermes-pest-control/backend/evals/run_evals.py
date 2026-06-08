from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.config.settings import Settings
from app.schemas.agent_response import AgentResponse
from app.schemas.incoming_message import IncomingMessage
from app.services.hermes_clients import default_business_context
from app.services.hermes_service import HermesService

DEFAULT_CASES_DIR = Path(__file__).resolve().parent / "cases"
SAFE_FALLBACK_SUMMARY = "Error procesando respuesta del agente. Requiere revisión humana."


@dataclass(frozen=True)
class EvaluationCase:
    id: str
    description: str
    input: dict[str, Any]
    expected: dict[str, Any]
    must_include_in_reply: list[str] = field(default_factory=list)
    must_not_include_in_reply: list[str] = field(default_factory=list)
    hermes_modes: list[str] = field(default_factory=lambda: ["mock", "real"])

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvaluationCase":
        return cls(
            id=data["id"],
            description=data.get("description", ""),
            input=data["input"],
            expected=data.get("expected", {}),
            must_include_in_reply=list(data.get("must_include_in_reply", [])),
            must_not_include_in_reply=list(data.get("must_not_include_in_reply", [])),
            hermes_modes=list(data.get("hermes_modes", ["mock", "real"])),
        )

    def supports_mode(self, hermes_mode: str) -> bool:
        return hermes_mode in self.hermes_modes


@dataclass
class EvaluationResult:
    eval_run_id: str
    case_id: str
    trace_id: str
    hermes_mode: str
    action_type: str
    incident_should_create: bool
    pest_type: str | None
    priority: str | None
    fallback_used: bool
    fallback_reason: str | None
    response_contract_version: str
    passed: bool
    failure_reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "eval_run_id": self.eval_run_id,
            "case_id": self.case_id,
            "trace_id": self.trace_id,
            "hermes_mode": self.hermes_mode,
            "action_type": self.action_type,
            "incident_should_create": self.incident_should_create,
            "pest_type": self.pest_type,
            "priority": self.priority,
            "fallback_used": self.fallback_used,
            "fallback_reason": self.fallback_reason,
            "response_contract_version": self.response_contract_version,
            "passed": self.passed,
            "failure_reasons": self.failure_reasons,
        }


@dataclass
class EvaluationSummary:
    eval_run_id: str
    results: list[EvaluationResult]

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for result in self.results if result.passed)

    @property
    def failed(self) -> int:
        return self.total - self.passed

    @property
    def exit_code(self) -> int:
        return 0 if self.failed == 0 else 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "eval_run_id": self.eval_run_id,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "results": [result.to_dict() for result in self.results],
        }


class EvaluationRunner:
    def __init__(
        self,
        hermes_service: HermesService | None = None,
        hermes_mode: str = "mock",
    ) -> None:
        self.hermes_mode = hermes_mode
        self.hermes_service = hermes_service or HermesService(
            settings=Settings(hermes_mode=hermes_mode)
        )

    async def run_cases(self, cases: list[EvaluationCase]) -> EvaluationSummary:
        eval_run_id = str(uuid4())
        results = []
        for evaluation_case in cases:
            results.append(await self.run_case(evaluation_case, eval_run_id))
        return EvaluationSummary(eval_run_id=eval_run_id, results=results)

    async def run_case(
        self,
        evaluation_case: EvaluationCase,
        eval_run_id: str,
    ) -> EvaluationResult:
        incoming_message = IncomingMessage.model_validate(evaluation_case.input)
        bus_ctx = default_business_context(evaluation_case.id)
        if evaluation_case.id != "sprint33_cucarachas_human_first_turn":
            bus_ctx["conversation_state"] = {"phase": "INTAKE"}
        response = await self.hermes_service.process_message(
            incoming_message,
            conversation_history=[],
            business_context=bus_ctx,
        )
        failure_reasons = evaluate_response(evaluation_case, response)
        incident_should_create = (
            response.incident.should_create if response.incident is not None else False
        )
        return EvaluationResult(
            eval_run_id=eval_run_id,
            case_id=evaluation_case.id,
            trace_id=str(uuid4()),
            hermes_mode=getattr(self.hermes_service, "hermes_mode", self.hermes_mode),
            action_type=response.action.type,
            incident_should_create=incident_should_create,
            pest_type=response.incident.pest_type if response.incident else None,
            priority=response.incident.priority if response.incident else None,
            fallback_used=is_safe_fallback(response),
            fallback_reason=response.metadata.get("fallback_reason"),
            response_contract_version="AgentResponse.v1",
            passed=not failure_reasons,
            failure_reasons=failure_reasons,
        )


def load_cases(cases_dir: Path = DEFAULT_CASES_DIR) -> list[EvaluationCase]:
    cases = []
    for case_file in sorted(cases_dir.glob("*.json")):
        with case_file.open(encoding="utf-8") as file:
            payload = json.load(file)

        if isinstance(payload, list):
            raw_cases = payload
        elif isinstance(payload, dict) and "cases" in payload:
            raw_cases = payload["cases"]
        elif isinstance(payload, dict):
            raw_cases = [payload]
        else:
            raise ValueError(f"Unsupported evaluation case file: {case_file}")

        cases.extend(EvaluationCase.from_dict(raw_case) for raw_case in raw_cases)
    return cases


def evaluate_response(
    evaluation_case: EvaluationCase,
    response: AgentResponse,
) -> list[str]:
    failure_reasons = []
    expected = evaluation_case.expected
    reply = response.reply.casefold()

    actual_values = {
        "action_type": response.action.type,
        "missing_fields": response.action.missing_fields,
        "should_create": (
            response.incident.should_create if response.incident is not None else None
        ),
        "pest_type": response.incident.pest_type if response.incident else None,
        "location": response.incident.location if response.incident else None,
        "affected_area": response.incident.affected_area if response.incident else None,
        "priority": response.incident.priority if response.incident else None,
    }

    for field_name, expected_value in expected.items():
        actual_value = actual_values.get(field_name)
        if actual_value != expected_value:
            failure_reasons.append(
                f"expected {field_name}={expected_value!r} got {field_name}={actual_value!r}"
            )

    for required_text in evaluation_case.must_include_in_reply:
        if required_text.casefold() not in reply:
            failure_reasons.append(f"reply must include {required_text!r}")

    for forbidden_text in evaluation_case.must_not_include_in_reply:
        if forbidden_text.casefold() in reply:
            failure_reasons.append(f"reply must not include {forbidden_text!r}")

    return failure_reasons


def is_safe_fallback(response: AgentResponse) -> bool:
    if response.metadata.get("fallback_used") is True:
        return True
    return (
        response.action.type == "escalate_to_human"
        and response.incident is not None
        and response.incident.summary == SAFE_FALLBACK_SUMMARY
    )


def print_summary(summary: EvaluationSummary) -> None:
    for result in summary.results:
        status = "PASS" if result.passed else "FAIL"
        print(f"[{status}] {result.case_id}")
        for reason in result.failure_reasons:
            print(f"  {reason}")

    print()
    print("Summary:")
    print(f"{summary.total} cases")
    print(f"{summary.passed} passed")
    print(f"{summary.failed} failed")


def write_results(summary: EvaluationSummary, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(summary.to_dict(), file, ensure_ascii=False, indent=2)
        file.write("\n")


async def run_evaluations(
    cases_dir: Path = DEFAULT_CASES_DIR,
    output_path: Path | None = None,
    hermes_mode: str = "mock",
) -> EvaluationSummary:
    cases = [
        evaluation_case
        for evaluation_case in load_cases(cases_dir)
        if evaluation_case.supports_mode(hermes_mode)
    ]
    summary = await EvaluationRunner(hermes_mode=hermes_mode).run_cases(cases)
    print_summary(summary)

    if output_path is not None:
        write_results(summary, output_path)
        print(f"Results written to {output_path}")

    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run offline Hermes evaluations.")
    parser.add_argument(
        "--cases-dir",
        type=Path,
        default=DEFAULT_CASES_DIR,
        help="Directory containing evaluation case JSON files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional JSON output path for evaluation results.",
    )
    parser.add_argument(
        "--hermes-mode",
        choices=["mock", "real"],
        default="mock",
        help="Hermes mode to evaluate. Defaults to mock.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = asyncio.run(
        run_evaluations(
            cases_dir=args.cases_dir,
            output_path=args.output,
            hermes_mode=args.hermes_mode,
        )
    )
    return summary.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
