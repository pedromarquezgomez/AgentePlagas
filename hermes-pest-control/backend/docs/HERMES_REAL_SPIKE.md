# Hermes Real Spike

## Purpose

Sprint 10A is a controlled technical spike for `HERMES_MODE=real`. The goal is
to validate the HTTP boundary around Hermes without making Telegram depend on a
real agent and without removing the safe fallback.

In this project, "Hermes real" means an external agent runtime that accepts the
same normalized message payload as `HermesRealClient` and returns a valid
`AgentResponse`.

## Current HermesRealClient Contract

`HermesRealClient` sends:

```json
{
  "message": {
    "channel": "...",
    "external_user_id": "...",
    "external_chat_id": "...",
    "message_type": "...",
    "text": "...",
    "attachments": [],
    "metadata": {}
  },
  "conversation_history": [],
  "business_context": {
    "domain": "pest_control",
    "company_type": "real_company",
    "language": "es",
    "agent_role": "operational_orchestrator"
  },
  "response_contract": "AgentResponse"
}
```

It expects a JSON response that validates as `AgentResponse`.

It handles:

- missing `HERMES_API_URL` with `HermesClientError`;
- network errors with `HermesClientError`;
- timeout with `HermesClientError`;
- HTTP `>=400` with `HermesClientError`;
- invalid JSON with `HermesClientError`;
- invalid `AgentResponse` contract with `HermesClientError`.

`HermesService` catches those errors and returns the safe
`escalate_to_human` fallback.

## Integration Options

### HTTP Endpoint

Hermes runs behind an HTTP API. The backend sends the payload above and receives
`AgentResponse`.

Pros:

- simple boundary;
- easy to mock with `httpx.MockTransport`;
- works with local or remote agent runtimes;
- good fit for current `HermesRealClient`.

Cons:

- needs timeout and retry policy before production;
- needs authentication and network controls.

### Local Process

Hermes runs as a local process invoked by Python.

Pros:

- low network complexity;
- useful for local experiments.

Cons:

- harder to deploy consistently;
- harder to sandbox;
- less aligned with cloud deployment.

### CLI Wrapper

Backend calls a CLI that wraps Hermes.

Pros:

- useful for one-off research workflows.

Cons:

- process management and parsing become fragile;
- not a good production boundary.

### Intermediate Server

A separate server adapts between Hermes internals and this backend contract.

Pros:

- isolates agent runtime complexity;
- allows independent deployment and observability.

Cons:

- more moving parts;
- still needs a stable HTTP contract.

## Recommended Option

Use the HTTP endpoint contract. Keep `HermesRealClient` as the backend boundary
and make any real Hermes runtime conform to `AgentResponse`.

For local development, use `backend/scripts/fake_hermes_server.py` as a contract
stub.

## Variables

```bash
HERMES_MODE=real
HERMES_API_URL=http://127.0.0.1:9000/agent
HERMES_API_KEY=
HERMES_TIMEOUT_SECONDS=30
```

`HERMES_API_KEY` is optional for the fake server. Do not log it.

## Fake Hermes Server

Start the fake server:

```bash
cd backend
source .venv/bin/activate
python scripts/fake_hermes_server.py
```

It exposes:

```text
POST http://127.0.0.1:9000/agent
```

Supported simulation triggers in message text:

- `fake_invalid_json`: returns invalid JSON.
- `fake_invalid_contract`: returns JSON that fails `AgentResponse`.
- `fake_error`: returns HTTP 500.
- `fake_timeout`: sleeps long enough to trigger timeout.

## Backend Test Flow

Terminal 1:

```bash
cd backend
source .venv/bin/activate
python scripts/fake_hermes_server.py
```

Terminal 2:

```bash
cd backend
source .venv/bin/activate
HERMES_MODE=real \
HERMES_API_URL=http://127.0.0.1:9000/agent \
uvicorn app.main:app --reload
```

Then call:

```bash
curl -X POST http://127.0.0.1:8000/messages/test \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "telegram",
    "external_user_id": "real-spike-user",
    "external_chat_id": "real-spike-chat",
    "message_type": "text",
    "text": "Tengo cucarachas en la cocina en Torremolinos desde hace una semana",
    "attachments": [],
    "metadata": {}
  }'
```

Expected:

- backend uses `HermesRealClient`;
- fake server returns valid `AgentResponse`;
- backend creates an incident when `should_create=true`;
- `DecisionRecord.hermes_mode` is `real`;
- no Telegram message is sent.

## Evaluation Mode

Default evaluations remain mock:

```bash
make evals
```

Optional real-mode evaluations:

```bash
HERMES_MODE=real HERMES_API_URL=http://127.0.0.1:9000/agent make evals-real
```

Do not use real-mode evaluations as a production gate until the real Hermes API,
prompt versions, and eval criteria are stable.

## Risks

- A real agent may return non-compliant JSON.
- Latency can degrade channel response time.
- Prompt or model changes can alter action decisions.
- Sensitive inputs must not be logged.
- Tool access must not be added without explicit permissions and audit.

## Next Steps

- Finalize the real Hermes HTTP contract.
- Add prompt and skill version values from configuration.
- Add retry policy only for safe/idempotent calls.
- Add latency and fallback metrics.
- Add real-mode eval CI job once a stable non-production Hermes endpoint exists.
