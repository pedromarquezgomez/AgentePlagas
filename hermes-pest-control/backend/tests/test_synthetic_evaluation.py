import json

import anyio

from app.schemas.agent_response import AgentResponse
from evals.synthetic.generate_synthetic_cases import (
    SyntheticCase,
    generate_template_cases,
    write_cases,
)
from evals.synthetic.run_synthetic_shadow_eval import (
    SyntheticShadowRunner,
    build_report,
    load_synthetic_cases,
)


def _response(
    action_type: str = "create_incident",
    priority: str = "high",
    pest_type: str | None = "cucarachas",
    fallback_used: bool = False,
) -> AgentResponse:
    metadata = {}
    if fallback_used:
        metadata = {
            "fallback_used": True,
            "fallback_reason": "HermesClientError:timeout",
        }
    return AgentResponse(
        reply="Respuesta controlada.",
        action={"type": action_type, "missing_fields": []},
        incident={
            "should_create": True,
            "pest_type": pest_type,
            "location": "Torremolinos",
            "affected_area": "cocina",
            "priority": priority,
            "summary": "Resumen.",
        },
        metadata=metadata,
    )


class StaticHermesService:
    hermes_mode = "mock"

    def __init__(self, response: AgentResponse) -> None:
        self.response = response
        self.calls = []

    async def process_message(self, incoming_message, **kwargs):
        self.calls.append((incoming_message, kwargs))
        return self.response


def test_template_generator_creates_valid_cases() -> None:
    cases = generate_template_cases(50, created_at="2026-06-02T00:00:00+00:00")

    assert len(cases) == 50
    assert all(case.case_id for case in cases)
    assert all(case.text for case in cases)
    assert any(case.safety_sensitive for case in cases)
    assert any(case.expected_action == "create_incident" for case in cases)
    assert any(case.expected_action == "collect_missing_data" for case in cases)


def test_write_and_load_synthetic_cases(tmp_path) -> None:
    output_path = tmp_path / "generated_cases.json"
    cases = generate_template_cases(3, created_at="2026-06-02T00:00:00+00:00")

    write_cases(cases, output_path)
    loaded = load_synthetic_cases(output_path)

    assert [case.case_id for case in loaded] == [case.case_id for case in cases]


def test_runner_processes_cases_without_openai_or_telegram() -> None:
    async def run():
        primary = StaticHermesService(_response())
        shadow = StaticHermesService(_response())
        runner = SyntheticShadowRunner(primary_service=primary, shadow_service=shadow)
        report = await runner.run_cases(generate_template_cases(2))
        return report, primary, shadow

    report, primary, shadow = anyio.run(run)

    assert report.total_cases == 2
    assert report.full_agreement_count == 2
    assert primary.calls[0][0].channel == "webchat"
    assert primary.calls[0][0].metadata["synthetic"] is True
    assert shadow.calls[0][0].channel == "webchat"


def test_report_contains_expected_metrics_for_differences() -> None:
    async def run():
        primary = StaticHermesService(_response(action_type="create_incident"))
        shadow = StaticHermesService(
            _response(
                action_type="escalate_to_human",
                priority="medium",
                pest_type=None,
                fallback_used=True,
            )
        )
        runner = SyntheticShadowRunner(primary_service=primary, shadow_service=shadow)
        return await runner.run_cases(generate_template_cases(1))

    report = anyio.run(run)

    assert report.total_cases == 1
    assert report.differences_count == 1
    assert report.shadow_error_count == 1
    assert report.action_mismatches == 1
    assert report.priority_mismatches == 1
    assert report.pest_type_mismatches == 1
    assert report.examples_of_differences[0]["shadow_fallback_reason"] == "HermesClientError:timeout"


def test_safety_sensitive_cases_are_identified() -> None:
    cases = generate_template_cases(50)

    assert any("producto" in case.text.casefold() and case.safety_sensitive for case in cases)
    assert any("perro" in case.text.casefold() and case.safety_sensitive for case in cases)


def test_build_report_is_json_serializable() -> None:
    async def run():
        runner = SyntheticShadowRunner(
            primary_service=StaticHermesService(_response()),
            shadow_service=StaticHermesService(_response()),
        )
        return await runner.run_cases(
            [
                SyntheticCase(
                    case_id="synthetic_test",
                    text="Tengo cucarachas en la cocina en Torremolinos",
                    expected_action="create_incident",
                    expected_priority="high",
                    expected_pest_type="cucarachas",
                    safety_sensitive=False,
                    notes="Test",
                    generated_by="template",
                    created_at="2026-06-02T00:00:00+00:00",
                )
            ]
        )

    report = anyio.run(run)

    json.dumps(report.to_dict())
