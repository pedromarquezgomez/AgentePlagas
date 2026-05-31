# Operations

Operational runbook for local development, Telegram E2E testing, configuration
diagnostics, and safe mode switching.

## Local Backend

From the project root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
scripts/run_dev.sh
```

Equivalent command:

```bash
uvicorn app.main:app --reload
```

The backend listens on:

```text
http://127.0.0.1:8000
```

## ngrok

On this Mac, start ngrok with the explicit loopback URL:

```bash
ngrok http http://127.0.0.1:8000
```

Do not use only `ngrok http 8000` if there are other services bound to
`localhost:8000`. In the Telegram E2E test, `localhost` resolved to another
backend, while `127.0.0.1` correctly reached Hermes.

Confirm the public URL reaches Hermes:

```bash
curl https://<NGROK_PUBLIC_URL>/health
```

Expected response:

```json
{
  "status": "ok"
}
```

## Telegram Webhook

Set these values in `backend/.env`:

```bash
TELEGRAM_BOT_TOKEN=123456:your-bot-token
TELEGRAM_WEBHOOK_URL=https://<NGROK_PUBLIC_URL>/webhooks/telegram
TELEGRAM_WEBHOOK_SECRET=
```

Configure the webhook:

```bash
cd backend
source .venv/bin/activate
python scripts/set_telegram_webhook.py
```

Inspect the webhook:

```bash
python scripts/get_telegram_webhook_info.py
```

Or through the backend:

```bash
curl http://127.0.0.1:8000/telegram/webhook-info
```

If ngrok restarts with a different URL, update `TELEGRAM_WEBHOOK_URL` and run
`set_telegram_webhook.py` again.

## Health Check

Local:

```bash
curl http://127.0.0.1:8000/health
```

Public through ngrok:

```bash
curl https://<NGROK_PUBLIC_URL>/health
```

## Configuration Status

Use this endpoint to verify safe runtime mode information:

```bash
curl http://127.0.0.1:8000/config/status
```

Example:

```json
{
  "app_env": "development",
  "hermes_mode": "mock",
  "telegram_configured": true,
  "firestore_mode": "mock",
  "firebase_project_id_configured": false,
  "admin_auth_required": false,
  "admin_api_key_configured": false
}
```

This endpoint never returns tokens, API keys, Firebase credentials, or raw
secrets.

## Admin Auth

Development mode can run without admin authentication:

```bash
REQUIRE_ADMIN_AUTH=false
ADMIN_API_KEY=
```

Protected mode requires an internal API key for operational endpoints:

```bash
REQUIRE_ADMIN_AUTH=true
ADMIN_API_KEY=change-this-long-random-value
```

When enabled, these endpoints require:

```text
X-Admin-API-Key: <ADMIN_API_KEY>
```

Protected endpoints:

- `GET /incidents`
- `GET /incidents/{incident_id}`
- `PATCH /incidents/{incident_id}`
- `GET /audit/decisions`
- `GET /audit/decisions/{decision_id}`

Public endpoints:

- `GET /health`
- `GET /config/status`
- `POST /webhooks/telegram`

`POST /messages/test` remains open for development. Disable or protect it before
production exposure.

Example protected request:

```bash
curl http://127.0.0.1:8000/incidents \
  -H "X-Admin-API-Key: <ADMIN_API_KEY>"
```

## Normalized Message Smoke Test

Run:

```bash
cd backend
scripts/smoke_test.sh
```

Or manually:

```bash
curl -X POST http://127.0.0.1:8000/messages/test \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "telegram",
    "external_user_id": "test-user-1",
    "external_chat_id": "test-chat-1",
    "message_type": "text",
    "text": "Tengo cucarachas en la cocina en Torremolinos desde hace una semana",
    "attachments": [],
    "metadata": {}
  }'
```

Expected:

```text
action.type=create_incident
incident.status=pending_review
```

## Running Evaluations

Run the offline Hermes evaluation suite:

```bash
make evals
```

Equivalent backend command:

```bash
cd backend
source .venv/bin/activate
python -m evals.run_evals
```

Optional JSON export:

```bash
python -m evals.run_evals --output evals/results/latest.json
```

The evaluation runner:

- loads cases from `backend/evals/cases`;
- builds `IncomingMessage` objects;
- executes `HermesService` in mock mode by default;
- checks expected `AgentResponse` fields;
- checks required and forbidden reply text;
- prints pass/fail results and a summary.

It does not call Telegram, does not send channel messages, and does not persist
evaluation traces to Firestore.

The optional JSON output includes decision-like fields such as `trace_id`,
`hermes_mode`, `action_type`, `incident_should_create`, `fallback_used`, and
`response_contract_version`.

## Decision Audit

Every message processed through `ConversationService` creates a structured
decision record in the `decision_records` collection.

List records:

```bash
curl http://127.0.0.1:8000/audit/decisions \
  -H "X-Admin-API-Key: <ADMIN_API_KEY>"
```

Filter records:

```bash
curl "http://127.0.0.1:8000/audit/decisions?conversation_id=telegram:test-user-1" \
  -H "X-Admin-API-Key: <ADMIN_API_KEY>"
curl "http://127.0.0.1:8000/audit/decisions?action_type=create_incident" \
  -H "X-Admin-API-Key: <ADMIN_API_KEY>"
curl "http://127.0.0.1:8000/audit/decisions?fallback_used=true" \
  -H "X-Admin-API-Key: <ADMIN_API_KEY>"
```

Get one record:

```bash
curl http://127.0.0.1:8000/audit/decisions/<decision_id> \
  -H "X-Admin-API-Key: <ADMIN_API_KEY>"
```

Decision records include traceability fields such as `trace_id`, `hermes_mode`,
`action_type`, `fallback_used`, `fallback_reason`, and
`response_contract_version`. They do not include Telegram tokens, Hermes API
keys, Firebase credentials, or full request headers.

## Incidents API

List incidents:

```bash
curl http://127.0.0.1:8000/incidents \
  -H "X-Admin-API-Key: <ADMIN_API_KEY>"
```

Filter by status or priority:

```bash
curl "http://127.0.0.1:8000/incidents?status=pending_review&priority=high" \
  -H "X-Admin-API-Key: <ADMIN_API_KEY>"
```

Get one incident:

```bash
curl http://127.0.0.1:8000/incidents/<incident_id> \
  -H "X-Admin-API-Key: <ADMIN_API_KEY>"
```

Update controlled operational fields:

```bash
curl -X PATCH http://127.0.0.1:8000/incidents/<incident_id> \
  -H "Content-Type: application/json" \
  -H "X-Admin-API-Key: <ADMIN_API_KEY>" \
  -d '{
    "status": "ready_for_scheduling",
    "priority": "high",
    "internal_notes": "Cliente disponible por las tardes."
  }'
```

Only these fields are editable from the API:

- `status`
- `priority`
- `internal_notes`

Allowed statuses:

```text
new
pending_review
waiting_for_client_data
ready_for_scheduling
scheduled
in_progress
completed
follow_up_pending
closed
cancelled
```

Allowed priorities:

```text
low
medium
high
urgent
```

## Incidents Panel

Install and run the frontend:

```bash
make frontend-install
make frontend-dev
```

Or manually:

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Default API URL:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_REQUIRE_LOGIN=true
```

If `VITE_REQUIRE_LOGIN=true`, open `/login`, enter `ADMIN_API_KEY`, and the
frontend stores it in localStorage. Requests to incidents and future audit views
send `X-Admin-API-Key`. Use the `Salir` button to clear localStorage.

Open:

```text
http://127.0.0.1:5173/incidents
```

Open one incident detail:

```text
http://127.0.0.1:5173/incidents/<incident_id>
```

If the backend has no incidents, the panel shows an empty state. If the backend
is unavailable, it shows an error state.

From the detail screen the operator can update:

- status
- priority
- internal notes

The detail screen shows saving, success, and error states. After saving, it
reloads the incident detail from the backend.

## Telegram Real E2E Test

Requirements:

- FastAPI running locally.
- ngrok running with `ngrok http http://127.0.0.1:8000`.
- Telegram webhook configured to `https://<NGROK_PUBLIC_URL>/webhooks/telegram`.
- `TELEGRAM_BOT_TOKEN` present in `backend/.env`.

Send this message to the Telegram bot:

```text
Tengo cucarachas en la cocina en Torremolinos desde hace una semana
```

Expected bot reply:

```text
Gracias por la información. He registrado el aviso para que el equipo lo revise...
```

## Hermes Mode

Mock mode:

```bash
HERMES_MODE=mock
HERMES_API_URL=
HERMES_API_KEY=
HERMES_TIMEOUT_SECONDS=30
```

Real mode:

```bash
HERMES_MODE=real
HERMES_API_URL=https://your-hermes-agent.example.com/process
HERMES_API_KEY=your-secret-api-key
HERMES_TIMEOUT_SECONDS=30
```

`HERMES_MODE=mock` keeps the deterministic local behavior. `HERMES_MODE=real`
uses the HTTP client prepared in `HermesRealClient`. If the real service fails,
times out, returns invalid JSON, or violates `AgentResponse`, Hermes falls back
to `escalate_to_human`.

## Firestore Mode

Mock persistence is used when:

```bash
APP_ENV=test
```

or in development when no real Firebase config is present:

```bash
APP_ENV=development
FIREBASE_CREDENTIALS_PATH=
FIREBASE_CREDENTIALS_JSON=
USE_FIRESTORE_EMULATOR=false
```

Real Firestore is used when any of these are configured:

```bash
FIREBASE_CREDENTIALS_PATH=/absolute/path/to/service-account.json
FIREBASE_CREDENTIALS_JSON='{"type":"service_account", "...":"..."}'
USE_FIRESTORE_EMULATOR=true
FIRESTORE_EMULATOR_HOST=127.0.0.1:8080
```

Never commit service account JSON files.

## Tests

Run:

```bash
cd backend
scripts/run_tests.sh
```

Or:

```bash
python -m pytest
```

From project root:

```bash
make test
```

## Make Commands

From project root:

```bash
make dev
make test
make smoke
make set-telegram-webhook
make telegram-webhook-info
make frontend-install
make frontend-dev
make frontend-build
```

## Expected Logs

Telegram webhook:

```text
Telegram webhook received update_id=...
IncomingMessage normalized channel=telegram external_user_id=... conversation_id=telegram:...
ConversationService completed channel=telegram external_user_id=... conversation_id=telegram:... action_type=create_incident incident_should_create=True
Telegram response sent channel=telegram external_user_id=... conversation_id=telegram:...
```

Hermes:

```text
hermes_request_started hermes_mode=mock
hermes_request_completed hermes_mode=mock action_type=create_incident
```

Fallback:

```text
hermes_response_invalid hermes_mode=real
hermes_fallback_used hermes_mode=real
```

Logs must not contain Telegram tokens, Hermes API keys, Firebase credentials,
full headers, or unnecessary customer text.

## Common Diagnostics

Confirm the public ngrok URL reaches Hermes, not another backend:

```bash
curl https://<NGROK_PUBLIC_URL>/openapi.json
```

Expected API title:

```text
Hermes Pest Control System
```

If the title is different, restart ngrok with:

```bash
ngrok http http://127.0.0.1:8000
```
