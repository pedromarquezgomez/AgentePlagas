from __future__ import annotations

import argparse
import json
from pathlib import Path

from evals.synthetic.generate_synthetic_cases import DEFAULT_OUTPUT_PATH, SyntheticCase

DEFAULT_EVALS_OUTPUT = Path(__file__).resolve().parents[1] / "cases" / "promoted_synthetic_cases.json"


def load_cases(path: Path) -> list[SyntheticCase]:
    data = json.loads(path.read_text(encoding="utf-8"))
    raw_cases = data["cases"] if isinstance(data, dict) and "cases" in data else data
    return [SyntheticCase.from_dict(raw_case) for raw_case in raw_cases]


def convert_case(case: SyntheticCase) -> dict:
    expected = {}
    if case.expected_action is not None:
        expected["action_type"] = case.expected_action
    if case.expected_priority is not None:
        expected["priority"] = case.expected_priority
    if case.expected_pest_type is not None:
        expected["pest_type"] = case.expected_pest_type
    return {
        "id": case.case_id,
        "description": f"Promoted synthetic case. {case.notes}",
        "input": {
            "channel": "webchat",
            "external_user_id": "eval-synthetic-user",
            "external_chat_id": "eval-synthetic-chat",
            "message_type": "text",
            "text": case.text,
            "attachments": [],
            "metadata": {"synthetic": True, "promoted": True},
        },
        "expected": expected,
        "must_include_in_reply": [],
        "must_not_include_in_reply": [],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manually promote selected synthetic cases into fixed eval cases."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_EVALS_OUTPUT)
    parser.add_argument(
        "--case-id",
        action="append",
        default=[],
        help="Case id to promote. Can be provided multiple times.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.case_id:
        raise SystemExit("Provide at least one --case-id. Promotion is intentionally manual.")
    cases = load_cases(args.input)
    selected = [case for case in cases if case.case_id in set(args.case_id)]
    missing = sorted(set(args.case_id) - {case.case_id for case in selected})
    if missing:
        raise SystemExit(f"Case ids not found: {', '.join(missing)}")

    payload = {"cases": [convert_case(case) for case in selected]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Promoted {len(selected)} cases to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
