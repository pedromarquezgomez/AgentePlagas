# Hermes Agent Integration

## Purpose

Sprint 10B connects the backend to a first Hermes Agent wrapper while preserving
the HTTP contract validated in Sprint 10A:

```text
HermesRealClient -> POST /agent -> AgentResponse
```

The wrapper is intentionally separate from the FastAPI business backend. It does
not write to Firestore, does not send Telegram messages, and does not bypass
`ConversationService`.

## Environment Findings

The repository currently contains:

- Hermes-facing backend services and schemas;
- the `HermesRealClient` HTTP boundary;
- the `FakeHermesServer` from Sprint 10A;
- Markdown skills under `hermes/skills`.

The repository does not currently contain:

- a standalone `hermes` CLI binary;
- a Hermes Agent SDK dependency in `backend/requirements.txt`;
- a Docker image or process definition for an external Hermes runtime.

Because of that, the chosen integration option for Sprint 10B is an HTTP wrapper
that loads the existing skills and exposes the already validated `POST /agent`
contract. The wrapper uses `HERMES_AGENT_MODE=local` as a deterministic local
adapter until a real Hermes runtime is available.

## Chosen Option

Implemented file:

```text
backend/scripts/hermes_agent_server.py
```

Endpoint:

```text
POST http://127.0.0.1:9100/agent
```

Input:

```json
{
  "message": {
    "channel": "telegram",
    "external_user_id": "123",
    "external_chat_id": "456",
    "message_type": "text",
    "text": "Tengo cucarachas en la cocina en Torremolinos",
    "attachments": [],
    "metadata": {}
  },
  "conversation_history": [],
  "business_context": {
    "domain": "pest_control"
  },
  "response_contract": "AgentResponse"
}
```

Output:

```json
{
  "reply": "Gracias por la información. He registrado el aviso para que el equipo lo revise.",
  "action": {
    "type": "create_incident",
    "missing_fields": []
  },
  "incident": {
    "should_create": true,
    "pest_type": "cucarachas",
    "location": "Torremolinos",
    "affected_area": "cocina",
    "priority": "high",
    "summary": "Cliente informa de presencia de cucarachas en cocina en Torremolinos."
  }
}
```

## Skill Loading

The wrapper loads these skills from `HERMES_SKILLS_DIR`:

- `02_pest_control_domain.md`
- `03_conversation_intake.md`
- `04_incident_lifecycle.md`
- `05_agent_response_contract.md`
- `06_human_escalation.md`
- `08_safety_and_compliance.md`

Current limitation:

There is no external Hermes runtime available in this repository yet, so the
wrapper cannot hand those skills to a real model/process. Instead, it builds the
same prompt context a real runtime would receive and uses a local deterministic
adapter to produce valid `AgentResponse` JSON.

This is deliberately not wired to Telegram by default.

## Configuration

Backend real mode still uses:

```bash
HERMES_MODE=real
HERMES_API_URL=http://127.0.0.1:9100/agent
HERMES_API_KEY=
HERMES_TIMEOUT_SECONDS=30
```

Wrapper-specific settings:

```bash
HERMES_AGENT_SERVER_PORT=9100
HERMES_SKILLS_DIR=../hermes/skills
HERMES_AGENT_MODE=local
```

Do not log API keys or raw customer text.

## How To Run

Terminal 1:

```bash
make hermes-agent-server
```

Terminal 2:

```bash
HERMES_MODE=real \
HERMES_API_URL=http://127.0.0.1:9100/agent \
make evals-hermes-agent
```

The equivalent lower-level command is:

```bash
cd backend
source .venv/bin/activate
HERMES_API_URL=http://127.0.0.1:9100/agent \
python -m evals.run_evals --hermes-mode real
```

## Manual Smoke With /messages/test

Terminal 1:

```bash
make hermes-agent-server
```

Terminal 2:

```bash
cd backend
source .venv/bin/activate
APP_ENV=test \
HERMES_MODE=real \
HERMES_API_URL=http://127.0.0.1:9100/agent \
uvicorn app.main:app --port 8010
```

Terminal 3:

```bash
curl -X POST http://127.0.0.1:8010/messages/test \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "telegram",
    "external_user_id": "hermes-agent-user",
    "external_chat_id": "hermes-agent-chat",
    "message_type": "text",
    "text": "Tengo cucarachas en la cocina en Torremolinos desde hace una semana",
    "attachments": [],
    "metadata": {}
  }'
```

Expected:

- response action is `create_incident`;
- incident status is `pending_review`;
- a decision record is created with `hermes_mode=real`;
- no Telegram message is sent.

## Contract Enforcement

The wrapper enforces `AgentResponse` by:

1. requiring `response_contract = "AgentResponse"`;
2. asking the local adapter/runtime to return only JSON;
3. extracting JSON from free text or fenced markdown if needed;
4. validating the result with Pydantic `AgentResponse`.

If validation fails, the wrapper returns HTTP `502`. `HermesRealClient` treats
that as a controlled error, and `HermesService` uses the safe
`escalate_to_human` fallback.

## Debugging Invalid Responses

Check:

- the wrapper logs for `hermes_agent_response_invalid`;
- whether the output contains parseable JSON;
- whether `action.type` is one of `create_incident`, `collect_missing_data`, or
  `escalate_to_human`;
- whether `incident.priority` is one of `low`, `medium`, `high`, or `urgent`;
- whether `response_contract` was sent as `AgentResponse`.

Keep logs safe:

- do not log Telegram tokens;
- do not log Hermes API keys;
- do not log Firebase credentials;
- avoid logging full customer text.

## Returning To Mock Mode

Use:

```bash
HERMES_MODE=mock
HERMES_API_URL=
```

Then run:

```bash
make evals
```

Mock mode remains the default and is the mode used for normal automated tests.

## Current Results

Current target for the local wrapper:

```text
make evals-hermes-agent
13 cases
13 passed
0 failed
```

These results validate the HTTP contract and wrapper behavior. They are not yet
a production-quality evaluation of a model-backed Hermes Agent.

## Next Steps

- Replace `HERMES_AGENT_MODE=local` with a real Hermes runtime mode when the
  runtime exists.
- Preserve `POST /agent` and `AgentResponse` as the backend-facing contract.
- Add prompt and skill version values to decision records from configuration.
- Add latency and invalid-response metrics around the wrapper.
- Add replay tests from stored conversations before routing Telegram traffic to
  any real model-backed agent.
