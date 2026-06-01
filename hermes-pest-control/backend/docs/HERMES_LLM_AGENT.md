# Hermes LLM Agent Mode

Sprint 18 adds a controlled LLM-backed mode to the existing Hermes Agent wrapper.
It does not activate the real agent in production by default.

## Boundary

The production application flow remains:

```text
ConversationService
  -> HermesService
  -> HermesRealClient
  -> HTTP /agent
  -> backend/scripts/hermes_agent_server.py
  -> LLM provider
  -> AgentResponse validated with Pydantic
```

The LLM wrapper must not write to Firestore, send Telegram/WhatsApp messages,
schedule visits, create documents, or perform side effects. Backend services
remain responsible for executing validated decisions.

## Modes

`HERMES_AGENT_MODE` supports:

- `fake`: deterministic development behavior, equivalent to the fake/local
  adapter boundary.
- `local`: deterministic skill-based wrapper used by default.
- `llm`: calls a real LLM provider from the wrapper.

The backend production pilot keeps:

```bash
HERMES_MODE=mock
HERMES_AGENT_MODE=local
```

## Configuration

Set these variables only in a local `.env`, shell session, Cloud Run secret/env
configuration, or Secret Manager. Do not commit real keys.

```bash
HERMES_AGENT_MODE=llm
LLM_PROVIDER=openai
OPENAI_API_KEY=<secret>
OPENAI_MODEL=<chosen-model>
OPENAI_TIMEOUT_SECONDS=30
AGENT_MAX_OUTPUT_TOKENS=1200
AGENT_TEMPERATURE=0
```

`OPENAI_MODEL` is intentionally explicit. Choose the model for the evaluation
budget, latency, and quality target before running controlled evals. Consult the
official OpenAI model and Structured Outputs documentation before promoting a
model choice.

Useful official docs:

- OpenAI Responses API: https://platform.openai.com/docs/api-reference/responses
- Structured Outputs: https://platform.openai.com/docs/guides/structured-outputs

## Running Locally

Terminal 1:

```bash
cd backend
source .venv/bin/activate
export HERMES_AGENT_MODE=llm
export LLM_PROVIDER=openai
export OPENAI_API_KEY=<secret>
export OPENAI_MODEL=<chosen-model>
python scripts/hermes_agent_server.py
```

Or from the repository root:

```bash
export OPENAI_API_KEY=<secret>
export OPENAI_MODEL=<chosen-model>
make hermes-agent-llm
```

Terminal 2:

```bash
HERMES_MODE=real \
HERMES_API_URL=http://127.0.0.1:9100/agent \
make evals-agent-llm
```

This is dry-run evaluation. It does not send Telegram, WhatsApp, emails, or
other channel messages.

## Contract Enforcement

The wrapper:

- builds a prompt from the system prompt, skills, incoming message,
  conversation history, business context, response contract, and safety rules;
- requests strict JSON compatible with `AgentResponse`;
- parses model output;
- validates with Pydantic;
- returns HTTP `502` on invalid model output so `HermesRealClient` and
  `HermesService` can trigger safe fallback.

The wrapper uses low temperature and bounded output tokens by default:

```bash
AGENT_TEMPERATURE=0
AGENT_MAX_OUTPUT_TOKENS=1200
OPENAI_TIMEOUT_SECONDS=30
```

## Interpreting Failures

If `make evals-agent-llm` fails:

- inspect which case failed and compare expected vs actual action;
- review whether the response violated the `AgentResponse` contract;
- check if fallback was used;
- inspect DecisionRecord-like eval output if an output file is used;
- adjust prompt/skills before considering model changes;
- keep production in `HERMES_MODE=mock`.

Common failure classes:

- missing required field in `AgentResponse`;
- wrong `action.type`;
- unsafe advice instead of escalation;
- over-eager incident creation with missing data;
- low-quality summary;
- timeout or provider HTTP error.

## Safeguards

- No OpenAI API calls are made in tests.
- API keys are never logged.
- Full prompts are not logged by default.
- Customer text should not be logged except under an explicit debug decision.
- Fallback remains active through `HermesService`.
- HumanReview remains active for fallback, `escalate_to_human`, and urgent
  cases.
- DecisionRecords continue to record `hermes_mode`, action type, fallback state,
  and trace IDs.

## Production Policy

Do not switch production Telegram to the LLM agent until:

1. `make evals-agent-llm` has been run and reviewed.
2. `/messages/test` has been tested against the wrapper in an isolated
   environment.
3. DecisionRecords are reviewed for quality and traceability.
4. Fallback and HumanReview are verified.
5. A staging Cloud Run service has been tested with internal traffic only.

Rollback remains simple:

```bash
HERMES_MODE=mock
```
