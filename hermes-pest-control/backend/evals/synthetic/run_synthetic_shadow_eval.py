from __future__ import annotations

import argparse
import asyncio
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.config.settings import Settings
from app.schemas.agent_response import AgentResponse
from app.schemas.incoming_message import IncomingMessage
from app.services.hermes_clients import default_business_context
from app.services.hermes_service import HermesService

from evals.run_evals import is_safe_fallback
from evals.synthetic.generate_synthetic_cases import (
    DEFAULT_OUTPUT_PATH,
    SyntheticCase,
)

DEFAULT_RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"


@dataclass(frozen=True)
class SyntheticDecision:
    action_type: str
    priority: str | None
    pest_type: str | None
    should_create: bool
    fallback_used: bool
    fallback_reason: str | None

    @classmethod
    def from_response(cls, response: AgentResponse) -> "SyntheticDecision":
        incident = response.incident
        return cls(
            action_type=response.action.type,
            priority=incident.priority if incident else None,
            pest_type=incident.pest_type if incident else None,
            should_create=incident.should_create if incident else False,
            fallback_used=is_safe_fallback(response),
            fallback_reason=response.metadata.get("fallback_reason"),
        )


@dataclass
class SyntheticCaseResult:
    case_id: str
    trace_id: str
    text: str
    safety_sensitive: bool
    expected_action: str | None
    expected_priority: str | None
    expected_pest_type: str | None
    primary: SyntheticDecision
    shadow: SyntheticDecision
    agreement_summary: str
    differences: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["primary"] = asdict(self.primary)
        payload["shadow"] = asdict(self.shadow)
        return payload


@dataclass
class SyntheticShadowReport:
    run_id: str
    created_at: str
    total_cases: int
    full_agreement_count: int
    differences_count: int
    shadow_error_count: int
    fallback_count: int
    safety_cases_correct: int
    action_mismatches: int
    priority_mismatches: int
    pest_type_mismatches: int
    examples_of_differences: list[dict[str, Any]]
    results: list[SyntheticCaseResult]

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "created_at": self.created_at,
            "total_cases": self.total_cases,
            "full_agreement_count": self.full_agreement_count,
            "differences_count": self.differences_count,
            "shadow_error_count": self.shadow_error_count,
            "fallback_count": self.fallback_count,
            "safety_cases_correct": self.safety_cases_correct,
            "action_mismatches": self.action_mismatches,
            "priority_mismatches": self.priority_mismatches,
            "pest_type_mismatches": self.pest_type_mismatches,
            "examples_of_differences": self.examples_of_differences,
            "results": [result.to_dict() for result in self.results],
        }


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def load_synthetic_cases(input_path: Path) -> list[SyntheticCase]:
    data = json.loads(input_path.read_text(encoding="utf-8"))
    raw_cases = data["cases"] if isinstance(data, dict) and "cases" in data else data
    return [SyntheticCase.from_dict(raw_case) for raw_case in raw_cases]


def build_incoming_message(case: SyntheticCase) -> IncomingMessage:
    return IncomingMessage(
        channel="webchat",
        external_user_id=f"synthetic-user-{case.case_id}",
        external_chat_id=f"synthetic-chat-{case.case_id}",
        message_type="text",
        text=case.text,
        attachments=[],
        metadata={
            "synthetic": True,
            "case_id": case.case_id,
            "source": "synthetic_shadow_eval",
        },
    )


def compare_decisions(
    primary: SyntheticDecision,
    shadow: SyntheticDecision,
) -> tuple[str, list[str]]:
    differences = []
    if primary.action_type != shadow.action_type:
        differences.append("action_type")
    if primary.priority != shadow.priority:
        differences.append("priority")
    if primary.pest_type != shadow.pest_type:
        differences.append("pest_type")
    if primary.should_create != shadow.should_create:
        differences.append("should_create")
    if shadow.fallback_used:
        differences.append("shadow_fallback")
    if not differences:
        return "full_agreement", []
    if shadow.fallback_used:
        return "shadow_error", differences
    return "differences_detected", differences


class SyntheticShadowRunner:
    def __init__(
        self,
        primary_service: HermesService | None = None,
        shadow_service: HermesService | None = None,
    ) -> None:
        self.primary_service = primary_service or HermesService(
            settings=Settings(app_env="test", hermes_mode="mock")
        )
        self.shadow_service = shadow_service or build_default_shadow_service()

    async def run_cases(self, cases: list[SyntheticCase]) -> SyntheticShadowReport:
        results = []
        for case in cases:
            results.append(await self.run_case(case))
        return build_report(results)

    async def run_case(self, case: SyntheticCase) -> SyntheticCaseResult:
        trace_id = str(uuid4())
        incoming = build_incoming_message(case)
        business_context = {
            **default_business_context(trace_id),
            "trace_id": trace_id,
            "synthetic": True,
            "case_id": case.case_id,
        }
        primary_response = await self.primary_service.process_message(
            incoming,
            conversation_history=[],
            business_context=business_context,
        )
        shadow_response = await self.shadow_service.process_message(
            incoming,
            conversation_history=[],
            business_context=business_context,
        )
        primary = SyntheticDecision.from_response(primary_response)
        shadow = SyntheticDecision.from_response(shadow_response)
        agreement_summary, differences = compare_decisions(primary, shadow)
        return SyntheticCaseResult(
            case_id=case.case_id,
            trace_id=trace_id,
            text=case.text,
            safety_sensitive=case.safety_sensitive,
            expected_action=case.expected_action,
            expected_priority=case.expected_priority,
            expected_pest_type=case.expected_pest_type,
            primary=primary,
            shadow=shadow,
            agreement_summary=agreement_summary,
            differences=differences,
            notes=case.notes,
        )


def build_default_shadow_service() -> HermesService:
    shadow_api_url = os.getenv("HERMES_SHADOW_API_URL", "") or os.getenv("HERMES_API_URL", "")
    if shadow_api_url:
        return HermesService(
            settings=Settings(
                app_env="test",
                hermes_mode="real",
                hermes_api_url=shadow_api_url,
                hermes_api_key=os.getenv("HERMES_API_KEY", ""),
                hermes_shadow_api_key=os.getenv("HERMES_SHADOW_API_KEY", ""),
                hermes_timeout_seconds=float(os.getenv("HERMES_SHADOW_TIMEOUT_SECONDS", "20")),
            )
        )
    return HermesService(settings=Settings(app_env="test", hermes_mode="mock"))


def build_report(results: list[SyntheticCaseResult]) -> SyntheticShadowReport:
    full_agreement_count = sum(1 for result in results if result.agreement_summary == "full_agreement")
    differences_count = len(results) - full_agreement_count
    shadow_error_count = sum(1 for result in results if result.shadow.fallback_used)
    fallback_count = sum(1 for result in results if result.primary.fallback_used or result.shadow.fallback_used)
    safety_cases_correct = sum(
        1
        for result in results
        if result.safety_sensitive
        and result.shadow.action_type == "escalate_to_human"
        and not result.shadow.fallback_used
    )
    action_mismatches = sum(1 for result in results if "action_type" in result.differences)
    priority_mismatches = sum(1 for result in results if "priority" in result.differences)
    pest_type_mismatches = sum(1 for result in results if "pest_type" in result.differences)
    examples = [
        {
            "case_id": result.case_id,
            "text": result.text,
            "agreement_summary": result.agreement_summary,
            "differences": result.differences,
            "primary_action_type": result.primary.action_type,
            "shadow_action_type": result.shadow.action_type,
            "primary_priority": result.primary.priority,
            "shadow_priority": result.shadow.priority,
            "primary_pest_type": result.primary.pest_type,
            "shadow_pest_type": result.shadow.pest_type,
            "shadow_fallback_reason": result.shadow.fallback_reason,
        }
        for result in results
        if result.differences
    ][:10]
    return SyntheticShadowReport(
        run_id=str(uuid4()),
        created_at=utc_now(),
        total_cases=len(results),
        full_agreement_count=full_agreement_count,
        differences_count=differences_count,
        shadow_error_count=shadow_error_count,
        fallback_count=fallback_count,
        safety_cases_correct=safety_cases_correct,
        action_mismatches=action_mismatches,
        priority_mismatches=priority_mismatches,
        pest_type_mismatches=pest_type_mismatches,
        examples_of_differences=examples,
        results=results,
    )


def write_report(report: SyntheticShadowReport, output_path: Path | None = None) -> Path:
    if output_path is None:
        output_path = DEFAULT_RESULTS_DIR / f"synthetic_shadow_report_{datetime.now(UTC):%Y%m%d_%H%M%S}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path


def print_summary(report: SyntheticShadowReport, output_path: Path) -> None:
    print("Synthetic shadow evaluation")
    print(f"total_cases={report.total_cases}")
    print(f"full_agreement_count={report.full_agreement_count}")
    print(f"differences_count={report.differences_count}")
    print(f"shadow_error_count={report.shadow_error_count}")
    print(f"fallback_count={report.fallback_count}")
    print(f"report={output_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run synthetic mock vs shadow evaluation.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path(os.getenv("SYNTHETIC_OUTPUT_PATH", DEFAULT_OUTPUT_PATH)),
    )
    parser.add_argument("--output", type=Path, default=None)
    return parser


async def run_synthetic_shadow_eval(input_path: Path, output_path: Path | None = None) -> SyntheticShadowReport:
    cases = load_synthetic_cases(input_path)
    report = await SyntheticShadowRunner().run_cases(cases)
    written_path = write_report(report, output_path)
    print_summary(report, written_path)
    return report


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.input.exists():
        raise SystemExit(
            f"Synthetic case file not found: {args.input}. Run make synthetic-cases first."
        )
    asyncio.run(run_synthetic_shadow_eval(args.input, args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
