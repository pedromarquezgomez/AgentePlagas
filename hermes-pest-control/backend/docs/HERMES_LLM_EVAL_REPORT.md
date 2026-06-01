# Hermes LLM Eval Report

Date: 2026-06-01

Status: blocked by missing local LLM configuration.

## Scope

Sprint 18.5 is intended to evaluate the controlled LLM-backed Hermes Agent
wrapper in a local/laboratory environment only.

Production remains unchanged:

- `HERMES_MODE=mock` stays active in production.
- Cloud Run was not changed.
- Telegram was not connected to the LLM agent.
- No real customer messages were sent through the LLM agent.
- The LLM wrapper has no Firestore or channel-send permissions.

## Intended Local Configuration

The following variables must be configured locally before running the real LLM
eval:

```bash
HERMES_AGENT_MODE=llm
LLM_PROVIDER=openai
OPENAI_API_KEY=<local-only-secret>
OPENAI_MODEL=<chosen-model>
OPENAI_TIMEOUT_SECONDS=30
AGENT_MAX_OUTPUT_TOKENS=800
AGENT_TEMPERATURE=0
```

Local configuration check on 2026-06-01:

- `OPENAI_API_KEY`: not configured.
- `OPENAI_MODEL`: not configured.
- `HERMES_AGENT_MODE`: not configured locally.
- `LLM_PROVIDER`: not configured locally.

Because `OPENAI_API_KEY` and `OPENAI_MODEL` were not configured, real LLM evals
were not executed. This avoids accidental execution with an unknown model or
missing credentials.

## Intended Commands

Terminal 1:

```bash
export HERMES_AGENT_MODE=llm
export LLM_PROVIDER=openai
export OPENAI_API_KEY=<local-only-secret>
export OPENAI_MODEL=<chosen-model>
export OPENAI_TIMEOUT_SECONDS=30
export AGENT_MAX_OUTPUT_TOKENS=800
export AGENT_TEMPERATURE=0
make hermes-agent-llm
```

Terminal 2:

```bash
HERMES_MODE=real \
HERMES_API_URL=http://127.0.0.1:9100/agent \
make evals-agent-llm
```

Optional JSON output:

```bash
cd backend
HERMES_MODE=real \
HERMES_API_URL=http://127.0.0.1:9100/agent \
python -m evals.run_evals \
  --hermes-mode real \
  --output evals/results/llm_eval_<date>.json
```

`backend/evals/results/` is ignored by Git for local lab results.

## Result Summary

Model used: not evaluated; `OPENAI_MODEL` missing.

Number of cases: 13 available in the current eval harness.

Cases passed: not executed.

Cases failed: not executed.

Failure counts:

| Failure type | Count |
| --- | ---: |
| classification | not evaluated |
| tone | not evaluated |
| safety | not evaluated |
| JSON invalid | not evaluated |
| incorrect action | not evaluated |
| incorrect priority | not evaluated |

## Findings

No behavioral findings can be made yet because the LLM provider was not
configured locally.

Configuration finding:

- Real LLM evaluation should remain blocked until both `OPENAI_API_KEY` and
  `OPENAI_MODEL` are explicitly set in the local shell or ignored local env.

## Recommended Classification Process For Future Failures

When real evals are run, classify each failed case as one of:

- base prompt problem;
- skill problem;
- JSON contract problem;
- evaluation case problem;
- model behavior problem.

Do not patch skills blindly. Only adjust a skill when the failed behavior is
clearly caused by missing or ambiguous project instruction.

## Candidate Behaviors To Watch

Current evals already cover:

- intoxication/safety escalation;
- pet exposure;
- food-business risk;
- angry customer escalation;
- complete pest intake;
- missing location/area data;
- chemical product request;
- mixing product request;
- guarantee request;
- fixed-price-without-data request.

If the LLM shows gaps, add or refine cases for:

- specific product recommendations;
- exposed pets or children;
- restaurant/bar/food business;
- ambiguous pest descriptions;
- aggressive or upset customer tone;
- requests for fixed price or guaranteed elimination.

## Readiness Decision

The LLM agent is **not ready for controlled production traffic** because real
LLM evals have not yet been executed.

Next step:

1. Configure `OPENAI_API_KEY` and `OPENAI_MODEL` locally.
2. Run `make hermes-agent-llm`.
3. Run `make evals-agent-llm`.
4. Save JSON results under `backend/evals/results/`.
5. Update this report with pass/fail counts and classified findings.

Production must remain in `HERMES_MODE=mock` until the above is complete and
reviewed.
