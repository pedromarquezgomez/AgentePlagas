# Synthetic Evaluation

Synthetic evaluation generates realistic pest-control intake messages and runs
them through a controlled comparison of Hermes mock versus a shadow Hermes LLM.
It exists to find disagreements without using Telegram, without contacting real
customers, and without modifying production prompts or skills automatically.

## What It Solves

Manual Telegram testing is useful for smoke checks, but it is slow and narrow.
Synthetic evaluation creates many varied scenarios so the team can inspect:

- action mismatches
- priority mismatches
- pest extraction differences
- safety-sensitive handling
- shadow fallback/error rates

## Generate Cases

Deterministic template generation is the default and does not call OpenAI:

```bash
make synthetic-cases
```

Equivalent explicit command:

```bash
cd backend
python -m evals.synthetic.generate_synthetic_cases \
  --mode template \
  --count 50 \
  --output backend/evals/synthetic/generated_cases.json
```

Optional LLM generation is controlled and never used by tests by default:

```bash
SYNTHETIC_GENERATION_MODE=llm \
SYNTHETIC_CASE_COUNT=50 \
OPENAI_API_KEY=... \
OPENAI_MODEL=gpt-4.1-mini \
make synthetic-cases
```

Do not commit secrets. Review generated cases before using them as fixed evals.

## Run Local Synthetic Shadow Evaluation

By default the runner uses `APP_ENV=test` style services and does not touch
Firestore real. If no shadow API URL is configured, it compares mock to mock,
which is useful for smoke and test reproducibility.

```bash
make synthetic-shadow-eval
```

To compare against a local Hermes LLM wrapper:

```bash
make hermes-agent-llm
```

In another terminal:

```bash
HERMES_SHADOW_API_URL=http://127.0.0.1:9100/agent \
HERMES_SHADOW_TIMEOUT_SECONDS=20 \
make synthetic-shadow-eval
```

The runner writes a report under:

```text
backend/evals/results/synthetic_shadow_report_YYYYMMDD_HHMMSS.json
```

## Report Fields

- `total_cases`: number of generated messages processed.
- `full_agreement_count`: primary and shadow matched on core fields.
- `differences_count`: number of cases with any core difference.
- `shadow_error_count`: shadow produced safe fallback or client error.
- `fallback_count`: primary or shadow used fallback.
- `safety_cases_correct`: safety-sensitive cases where shadow escalated without fallback.
- `action_mismatches`: action type differs.
- `priority_mismatches`: priority differs.
- `pest_type_mismatches`: pest extraction differs.
- `examples_of_differences`: compact review queue for humans.

## Controlled Cloud Pilot Mode

`make synthetic-shadow-eval-cloud` is intentionally explicit. Use it only for a
controlled pilot and mark every case as synthetic. Confirm the configured URL
and API key source before running.

This command must not be part of default CI or routine tests.

## Promote Cases To Fixed Evals

Interesting synthetic cases can be promoted manually:

```bash
cd backend
python -m evals.synthetic.promote_cases_to_evals \
  --case-id synthetic_template_0001_cockroaches_kitchen_complete
```

Promotion does not change skills or prompts. A human must review the expected
fields before committing promoted evals.

## Safety Rules

- Do not send synthetic messages to Telegram or WhatsApp.
- Do not send messages to customers.
- Do not activate `HERMES_MODE=real` in production for this workflow.
- Do not allow synthetic evals to auto-edit skills or prompts.
- Do not store OpenAI keys or Cloud Run secrets in Git.
- Treat reports as diagnostic evidence, not automatic training data.
