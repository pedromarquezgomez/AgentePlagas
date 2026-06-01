# Hermes LLM Shadow Mode Runbook

Shadow Mode runs a secondary Hermes endpoint in parallel with the active Hermes
decision. The active response remains the source of truth.

The production pilot must keep:

```bash
HERMES_MODE=mock
```

Shadow Mode is audit-only. It must not send messages, create incidents, modify
visits, update technicians, generate documents, or change calendar state.

## What It Does

When enabled, `ConversationService`:

1. Processes the incoming message with the primary `HermesService`.
2. Uses the primary response for the customer reply and all business actions.
3. Calls the configured shadow Hermes endpoint.
4. Compares primary and shadow decisions.
5. Writes one `ShadowDecisionRecord` to `shadow_decision_records`.

If the shadow call fails, the primary flow continues.

## Configuration

```bash
HERMES_SHADOW_MODE=false
HERMES_SHADOW_API_URL=
HERMES_SHADOW_API_KEY=
HERMES_SHADOW_SAMPLE_RATE=1.0
HERMES_SHADOW_TIMEOUT_SECONDS=20
```

Rules:

- `HERMES_SHADOW_MODE=false`: no shadow call is made.
- `HERMES_SHADOW_MODE=true`: shadow is considered.
- `HERMES_SHADOW_API_URL` must be configured, otherwise shadow is skipped.
- `HERMES_SHADOW_API_KEY`, when configured, is sent as
  `X-Hermes-Agent-Key` to the shadow agent service.
- `HERMES_SHADOW_SAMPLE_RATE=0.1` means around 10 percent of messages are
  sampled.

Do not store `OPENAI_API_KEY` in Git. Use local `.env` files, Cloud Run
environment variables, or Secret Manager.

## Local Controlled Smoke

Create local-only LLM config:

```bash
cd backend
cat > .env.llm.local <<'EOF'
OPENAI_API_KEY=<secret>
OPENAI_MODEL=gpt-4.1-mini
HERMES_AGENT_MODE=llm
LLM_PROVIDER=openai
OPENAI_TIMEOUT_SECONDS=30
AGENT_MAX_OUTPUT_TOKENS=800
AGENT_TEMPERATURE=0
EOF
chmod 600 .env.llm.local
```

`backend/.env.llm.local` is ignored by Git.

Run the local smoke:

```bash
cd "/Users/pedro/AgentePlagas /hermes-pest-control"
backend/scripts/run_shadow_smoke_local.sh
```

The script:

- loads `backend/.env.llm.local`;
- starts the local Hermes LLM wrapper;
- starts the backend with `HERMES_MODE=mock` and shadow enabled;
- posts one controlled `/messages/test` request;
- verifies that a `ShadowDecisionRecord` exists;
- stops both local processes;
- never prints `OPENAI_API_KEY`.

Safe logs:

```bash
tail -n 80 /tmp/hermes-agent-llm-shadow-smoke.log
tail -n 80 /tmp/hermes-backend-shadow-smoke.log
```

## Querying Shadow Records

Protected endpoints:

```text
GET /audit/shadow-decisions
GET /audit/shadow-decisions/{id}
```

Filters:

```text
conversation_id
channel
shadow_action_type
limit
```

Local example:

```bash
curl "http://127.0.0.1:8000/audit/shadow-decisions?limit=20"
```

Production example with Firebase Auth:

```bash
curl -H "Authorization: Bearer <firebase-id-token>" \
  "https://<cloud-run-url>/audit/shadow-decisions?limit=20"
```

## Diagnosing Shadow Failures

Every shadow call propagates the `ConversationService` trace as:

```text
X-Hermes-Trace-Id: <trace_id>
```

Backend logs to check:

```text
hermes_real_client_error trace_id=... error_type=... error_class=... status_code=...
hermes_response_invalid hermes_mode=real error_type=... status_code=...
hermes_fallback_used hermes_mode=real
hermes_shadow_record_created trace_id=... shadow_error=...
```

Agent wrapper logs to check:

```text
hermes_agent_request_started trace_id=... agent_mode=...
hermes_agent_skills_loaded trace_id=... skills_count=6 ...
hermes_llm_request_started trace_id=... provider=openai ...
hermes_llm_request_completed trace_id=...
hermes_agent_response_valid trace_id=... response_valid=true ...
hermes_agent_response_invalid trace_id=... response_valid=false error_type=...
```

`ShadowDecisionRecord.shadow_error` uses normalized safe values:

```text
HermesClientError:timeout
HermesClientError:connection_error
HermesClientError:request_failed
HermesClientError:http_401
HermesClientError:http_500
HermesClientError:invalid_json
HermesClientError:invalid_contract
UnexpectedError:<ExceptionClass>
```

If backend logs show `hermes_real_client_error` but the wrapper has no matching
`hermes_agent_request_started` for the same `trace_id`, the request failed
before reaching the wrapper. If the wrapper has the trace but no
`hermes_llm_request_started`, the failure happened before the LLM call, usually
auth, contract, or skill loading. If OpenAI was called and the wrapper returns
502, inspect `hermes_agent_response_invalid` and the normalized shadow error.

## Cloud Run Controlled Activation

Do not enable this unless the LLM endpoint has already passed lab evals.

Deploy the separate LLM wrapper first:

```bash
export GOOGLE_CLOUD_PROJECT=control-plagas-ai
export REGION=europe-west1
export CLOUD_RUN_SERVICE=hermes-agent-llm
scripts/deploy_hermes_agent_llm_cloud_run.sh
```

Current prepared wrapper URL:

```text
https://hermes-agent-llm-601698914613.europe-west1.run.app
```

The deploy script expects these Secret Manager secrets to exist by default:

```text
openai-api-key
hermes-agent-api-key
```

The agent validates incoming `POST /agent` requests with:

```text
X-Hermes-Agent-Key: <secret>
```

The public `/health` endpoint remains available for readiness checks.

Recommended first production pilot values:

```bash
HERMES_MODE=mock
HERMES_SHADOW_MODE=true
HERMES_SHADOW_API_URL=https://hermes-agent-llm-601698914613.europe-west1.run.app/agent
HERMES_SHADOW_API_KEY=<same value as hermes-agent-api-key>
HERMES_SHADOW_SAMPLE_RATE=0.1
HERMES_SHADOW_TIMEOUT_SECONDS=20
```

If the shadow wrapper runs as a separate Cloud Run service, configure
`OPENAI_API_KEY` only on that wrapper service, preferably through Secret
Manager. The main backend only needs `HERMES_SHADOW_API_URL`.

Example update:

```bash
gcloud run services update hermes-pest-control-backend \
  --region europe-west1 \
  --update-env-vars HERMES_MODE=mock,HERMES_SHADOW_MODE=true,HERMES_SHADOW_API_URL=https://hermes-agent-llm-601698914613.europe-west1.run.app/agent,HERMES_SHADOW_SAMPLE_RATE=0.1,HERMES_SHADOW_TIMEOUT_SECONDS=20
```

## Fast Disable

Disable shadow immediately:

```bash
gcloud run services update hermes-pest-control-backend \
  --region europe-west1 \
  --update-env-vars HERMES_SHADOW_MODE=false
```

Local disable:

```bash
unset HERMES_SHADOW_MODE
```

or set:

```bash
HERMES_SHADOW_MODE=false
```

## Pre-Activation Checklist

- `HERMES_MODE=mock`.
- `HERMES_SHADOW_API_URL` configured.
- `HERMES_SHADOW_SAMPLE_RATE` starts at `0.1` or lower in production.
- LLM evals pass in lab.
- `/messages/test` smoke passes locally or in staging.
- `/ready` is healthy/degraded only for known non-blocking reasons.
- Admin auth works for `/audit/shadow-decisions`.
- Logs do not print `OPENAI_API_KEY`, prompts, or unnecessary customer text.

## Post-Activation Checklist

- Send one controlled Telegram message.
- Confirm the user receives the normal primary mock response.
- Confirm the expected incident is created by the primary flow.
- Confirm a `ShadowDecisionRecord` is written.
- Review `agreement_summary` and `differences`.
- Confirm no extra incidents, visits, documents, or calendar events were
  created by shadow.
- Disable shadow if errors or costs spike.

## Risks And Costs

- Each sampled message can call the LLM provider.
- Provider latency does not affect the customer response if shadow errors are
  contained, but it still adds backend work after primary processing.
- Shadow records may contain operational summaries and extracted fields; protect
  audit endpoints with admin auth.
- Prompt or schema changes can change shadow comparison behavior.
- Do not use shadow results for automation until they have been reviewed.
