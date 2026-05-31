import json

import anyio

from app.schemas.agent_response import AgentResponse
from evals.run_evals import (
    EvaluationCase,
    EvaluationRunner,
    evaluate_response,
    load_cases,
)


def _case_data(expected: dict | None = None) -> dict:
    return {
        "id": "test_case",
        "description": "Test case",
        "input": {
            "channel": "telegram",
            "external_user_id": "eval-user",
            "external_chat_id": "eval-chat",
            "message_type": "text",
            "text": "Tengo cucarachas en la cocina en Torremolinos",
            "attachments": [],
            "metadata": {},
        },
        "expected": expected or {"action_type": "create_incident"},
        "must_include_in_reply": [],
        "must_not_include_in_reply": [],
    }


def _agent_response(reply: str = "Caso registrado por el equipo.") -> AgentResponse:
    return AgentResponse(
        reply=reply,
        action={"type": "create_incident", "missing_fields": []},
        incident={
            "should_create": True,
            "pest_type": "cucarachas",
            "location": "Torremolinos",
            "affected_area": "cocina",
            "priority": "high",
            "summary": "Cliente informa de cucarachas.",
        },
    )


class StaticHermesService:
    hermes_mode = "mock"

    def __init__(self, response: AgentResponse) -> None:
        self.response = response

    async def process_message(self, *_args, **_kwargs) -> AgentResponse:
        return self.response


def test_load_cases_reads_json_case_files(tmp_path) -> None:
    cases_dir = tmp_path / "cases"
    cases_dir.mkdir()
    (cases_dir / "sample.json").write_text(
        json.dumps({"cases": [_case_data()]}),
        encoding="utf-8",
    )

    cases = load_cases(cases_dir)

    assert len(cases) == 1
    assert cases[0].id == "test_case"


def test_expected_case_passes() -> None:
    evaluation_case = EvaluationCase.from_dict(
        _case_data(
            {
                "action_type": "create_incident",
                "pest_type": "cucarachas",
                "location": "Torremolinos",
                "affected_area": "cocina",
                "priority": "high",
                "should_create": True,
            }
        )
    )

    failure_reasons = evaluate_response(evaluation_case, _agent_response())

    assert failure_reasons == []


def test_incorrect_expected_case_fails() -> None:
    evaluation_case = EvaluationCase.from_dict(
        _case_data({"action_type": "collect_missing_data"})
    )

    failure_reasons = evaluate_response(evaluation_case, _agent_response())

    assert failure_reasons == [
        "expected action_type='collect_missing_data' got action_type='create_incident'"
    ]


def test_must_not_include_detects_forbidden_reply_text() -> None:
    case_data = _case_data({"action_type": "create_incident"})
    case_data["must_not_include_in_reply"] = ["precio cerrado"]
    evaluation_case = EvaluationCase.from_dict(case_data)

    failure_reasons = evaluate_response(
        evaluation_case,
        _agent_response("Te doy precio cerrado ahora."),
    )

    assert failure_reasons == ["reply must not include 'precio cerrado'"]


def test_runner_summary_exit_code_reflects_failures() -> None:
    async def run() -> tuple[int, int]:
        passing_case = EvaluationCase.from_dict(
            _case_data({"action_type": "create_incident"})
        )
        failing_case = EvaluationCase.from_dict(
            {
                **_case_data({"action_type": "collect_missing_data"}),
                "id": "failing_case",
            }
        )
        runner = EvaluationRunner(
            hermes_service=StaticHermesService(_agent_response()),
            hermes_mode="mock",
        )
        summary = await runner.run_cases([passing_case, failing_case])
        return summary.failed, summary.exit_code

    failed, exit_code = anyio.run(run)

    assert failed == 1
    assert exit_code == 1
