# Operations

Operational runbook for local development, Telegram and WhatsApp channel
testing, configuration diagnostics, and safe mode switching.

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

## WhatsApp Webhook

WhatsApp is optional and disabled by default. It uses the same normalized
message flow as Telegram:

```text
Meta WhatsApp payload -> WhatsAppAdapter -> ConversationService -> HermesService
```

Local sandbox mode does not call Meta:

```bash
WHATSAPP_ENABLED=true
WHATSAPP_PROVIDER=mock
```

Run the backend, then execute:

```bash
cd backend
source .venv/bin/activate
scripts/smoke_whatsapp_payload.sh
```

The script posts a simulated WhatsApp Cloud API payload to
`POST /webhooks/whatsapp`. In mock provider mode, outbound sending is simulated
and no WhatsApp token is required. The expected result is:

```json
{
  "status": "ok"
}
```

For Meta WhatsApp Cloud API, configure:

```bash
WHATSAPP_ENABLED=true
WHATSAPP_PROVIDER=meta
WHATSAPP_VERIFY_TOKEN=choose-a-webhook-verify-token
WHATSAPP_ACCESS_TOKEN=<meta-access-token>
WHATSAPP_PHONE_NUMBER_ID=<phone-number-id>
WHATSAPP_WEBHOOK_SECRET=
WHATSAPP_GRAPH_API_VERSION=v20.0
```

Meta webhook verification uses:

```text
GET /webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=<token>&hub.challenge=<challenge>
```

Inbound messages use:

```text
POST /webhooks/whatsapp
```

If `WHATSAPP_WEBHOOK_SECRET` is configured, requests must include:

```text
X-Whatsapp-Webhook-Secret: <WHATSAPP_WEBHOOK_SECRET>
```

Do not commit access tokens or service credentials. `/config/status` only
reports whether WhatsApp values are configured.

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
  "hermes_api_url_configured": false,
  "hermes_api_key_configured": false,
  "hermes_agent_mode": "local",
  "hermes_skills_dir_configured": true,
  "telegram_configured": true,
  "firestore_mode": "mock",
  "firebase_project_id_configured": false,
  "firebase_credentials_configured": false,
  "firestore_emulator_enabled": false,
  "auth_mode": "api_key",
  "firebase_auth_enabled": false,
  "admin_auth_required": false,
  "admin_api_key_configured": false,
  "whatsapp_enabled": false,
  "whatsapp_provider": "meta",
  "whatsapp_access_token_configured": false,
  "whatsapp_phone_number_id_configured": false,
  "whatsapp_verify_token_configured": false
}
```

This endpoint never returns tokens, API keys, Firebase credentials, or raw
secrets.

## Admin Auth

The backend supports three operator-auth modes for operational endpoints:

- `AUTH_MODE=api_key`: keeps the existing internal API-key guard.
- `AUTH_MODE=firebase`: requires a Firebase ID token in the `Authorization`
  header.
- `AUTH_MODE=disabled`: local development only; rejected in production.

API-key development mode can run without enforcement:

```bash
AUTH_MODE=api_key
REQUIRE_ADMIN_AUTH=false
ADMIN_API_KEY=
```

API-key protected mode:

```bash
AUTH_MODE=api_key
REQUIRE_ADMIN_AUTH=true
ADMIN_API_KEY=change-this-long-random-value
```

API-key requests require:

```text
X-Admin-API-Key: <ADMIN_API_KEY>
```

Firebase Auth mode:

```bash
AUTH_MODE=firebase
FIREBASE_AUTH_ENABLED=true
FIREBASE_PROJECT_ID=<firebase-project-id>
FIREBASE_CREDENTIALS_PATH=/absolute/path/to/firebase-service-account.json
```

Firebase requests require:

```text
Authorization: Bearer <Firebase ID token>
```

Create the first operator manually in Firebase Console > Authentication > Users
with email/password. The frontend login uses that email/password and sends the
Firebase ID token to the backend. No roles or multi-company claims are enforced
yet.

Protected endpoints:

- `GET /incidents`
- `GET /incidents/{incident_id}`
- `PATCH /incidents/{incident_id}`
- `GET /dashboard/summary`
- `GET /calendar/visits`
- `GET /audit/decisions`
- `GET /audit/decisions/{decision_id}`
- `GET /human-review`
- `GET /human-review/{item_id}`
- `PATCH /human-review/{item_id}`
- `GET /technicians`
- `POST /technicians`
- `GET /technicians/{technician_id}`
- `PATCH /technicians/{technician_id}`
- `GET /visits`
- `POST /visits`
- `GET /visits/{visit_id}`
- `PATCH /visits/{visit_id}`
- `POST /visits/{visit_id}/sync-calendar`
- `GET /documents`
- `POST /documents`
- `GET /documents/{document_id}`
- `PATCH /documents/{document_id}`
- `POST /incidents/{incident_id}/generate-summary-document`
- `POST /visits/{visit_id}/generate-technician-brief`

Public endpoints:

- `GET /health`
- `GET /config/status`
- `POST /webhooks/telegram`
- `GET /webhooks/whatsapp`
- `POST /webhooks/whatsapp`

`POST /messages/test` remains open for development. Disable or protect it before
production exposure.

Example protected request:

```bash
curl http://127.0.0.1:8000/incidents \
  -H "X-Admin-API-Key: <ADMIN_API_KEY>"
```

Firebase protected request:

```bash
curl http://127.0.0.1:8000/incidents \
  -H "Authorization: Bearer <FIREBASE_ID_TOKEN>"
```

## Dashboard Summary

The operational dashboard uses a protected aggregate endpoint:

```bash
curl http://127.0.0.1:8000/dashboard/summary \
  -H "X-Admin-API-Key: <ADMIN_API_KEY>"
```

It returns safe counters only: incidents, human review items, visits, and
technicians. It does not expose customer message text, API keys, Telegram
tokens, or Firebase credentials.

## Calendar Visits API

The internal calendar reads visits by date range. It is read-only; Hermes does
not assign technicians, create visits, or modify the agenda.

```bash
curl "http://127.0.0.1:8000/calendar/visits?start_date=2026-06-01&end_date=2026-06-07" \
  -H "X-Admin-API-Key: <ADMIN_API_KEY>"
```

Optional filters:

```bash
curl "http://127.0.0.1:8000/calendar/visits?start_date=2026-06-01&end_date=2026-06-07&technician_id=<technician_id>&status=scheduled" \
  -H "X-Admin-API-Key: <ADMIN_API_KEY>"
```

`start_date` and `end_date` are required. The backend returns `422` if the dates
are missing or if `end_date` is earlier than `start_date`.

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

## Human Review Queue

Every message processed through `ConversationService` can create a human review
item after the decision record is persisted.

Items are created when:

- `action.type=escalate_to_human`;
- `fallback_used=true`;
- incident priority is `urgent`;
- response metadata marks `sensitive_case=true`.

List review items:

```bash
curl http://127.0.0.1:8000/human-review \
  -H "X-Admin-API-Key: <ADMIN_API_KEY>"
```

Filter by status or priority:

```bash
curl "http://127.0.0.1:8000/human-review?status=open&priority=urgent" \
  -H "X-Admin-API-Key: <ADMIN_API_KEY>"
```

Get one item:

```bash
curl http://127.0.0.1:8000/human-review/<item_id> \
  -H "X-Admin-API-Key: <ADMIN_API_KEY>"
```

Resolve or dismiss an item:

```bash
curl -X PATCH http://127.0.0.1:8000/human-review/<item_id> \
  -H "Content-Type: application/json" \
  -H "X-Admin-API-Key: <ADMIN_API_KEY>" \
  -d '{
    "status": "resolved",
    "assigned_to": "operador",
    "resolution_notes": "Caso revisado y resuelto por teléfono."
  }'
```

PATCH only accepts:

- `status`;
- `assigned_to`;
- `resolution_notes`.

Allowed statuses:

```text
open
in_review
resolved
dismissed
```

When status is `resolved` or `dismissed`, the backend sets `resolved_at`
automatically.

## Technicians API

Technicians are managed manually by operators. Hermes does not create,
update, or assign technicians.

List technicians:

```bash
curl http://127.0.0.1:8000/technicians \
  -H "X-Admin-API-Key: <ADMIN_API_KEY>"
```

Create technician:

```bash
curl -X POST http://127.0.0.1:8000/technicians \
  -H "Content-Type: application/json" \
  -H "X-Admin-API-Key: <ADMIN_API_KEY>" \
  -d '{
    "name": "Ana Técnica",
    "phone": "+34111111111",
    "email": "ana@example.com",
    "active": true,
    "service_area": "Málaga",
    "skills": ["cucarachas", "roedores"]
  }'
```

PATCH only accepts:

- `name`
- `phone`
- `email`
- `active`
- `service_area`
- `skills`

## Visits API

Visits are agenda entries associated with incidents. Creation and assignment are
manual from the panel or API. There is no route optimization. Google Calendar
sync is optional and manual; Firestore remains the source of truth.

List visits:

```bash
curl http://127.0.0.1:8000/visits \
  -H "X-Admin-API-Key: <ADMIN_API_KEY>"
```

Filter visits:

```bash
curl "http://127.0.0.1:8000/visits?incident_id=<incident_id>&status=scheduled" \
  -H "X-Admin-API-Key: <ADMIN_API_KEY>"
```

Create visit:

```bash
curl -X POST http://127.0.0.1:8000/visits \
  -H "Content-Type: application/json" \
  -H "X-Admin-API-Key: <ADMIN_API_KEY>" \
  -d '{
    "incident_id": "<incident_id>",
    "technician_id": "<technician_id>",
    "scheduled_start": "2026-06-01T09:00:00+02:00",
    "scheduled_end": "2026-06-01T10:00:00+02:00",
    "status": "scheduled",
    "address": "Dirección del aviso",
    "notes": "Primera visita."
  }'
```

PATCH only accepts:

- `technician_id`
- `scheduled_start`
- `scheduled_end`
- `status`
- `address`
- `notes`

Allowed visit statuses:

```text
draft
scheduled
in_progress
completed
cancelled
```

## Optional Google Calendar Sync

Google Calendar is disabled by default:

```bash
GOOGLE_CALENDAR_ENABLED=false
GOOGLE_CALENDAR_ID=
GOOGLE_CALENDAR_CREDENTIALS_PATH=
GOOGLE_CALENDAR_CREDENTIALS_JSON=
```

With sync disabled, the endpoint returns a controlled skipped response and does
not call Google:

```bash
curl -X POST http://127.0.0.1:8000/visits/<visit_id>/sync-calendar \
  -H "X-Admin-API-Key: <ADMIN_API_KEY>"
```

Expected disabled response:

```json
{
  "status": "skipped",
  "reason": "google_calendar_disabled"
}
```

To enable real sync, create a Google service account with access to the target
calendar, share the calendar with that service account email, and set either:

```bash
GOOGLE_CALENDAR_ENABLED=true
GOOGLE_CALENDAR_ID=your-calendar-id
GOOGLE_CALENDAR_CREDENTIALS_PATH=/absolute/path/outside/repo/google-calendar-service-account.json
```

or:

```bash
GOOGLE_CALENDAR_ENABLED=true
GOOGLE_CALENDAR_ID=your-calendar-id
GOOGLE_CALENDAR_CREDENTIALS_JSON='{"type":"service_account","...":"..."}'
```

The sync stores only these fields on the visit:

- `external_calendar_provider`
- `external_calendar_event_id`
- `external_calendar_sync_status`
- `external_calendar_last_synced_at`
- `external_calendar_error`

Risks and limitations:

- Google Calendar is not the system of record.
- OAuth user consent is not implemented in this sprint.
- Sync is manual from the visit detail or API.
- Tests mock `GoogleCalendarService` and do not call Google.

## Operational Documents API

Documents are internal operational drafts, not official legal certificates.
Hermes does not create documents directly.

```bash
curl http://127.0.0.1:8000/documents \
  -H "X-Admin-API-Key: <ADMIN_API_KEY>"
```

Generate template-based documents:

```bash
curl -X POST http://127.0.0.1:8000/incidents/<incident_id>/generate-summary-document \
  -H "X-Admin-API-Key: <ADMIN_API_KEY>"

curl -X POST http://127.0.0.1:8000/visits/<visit_id>/generate-technician-brief \
  -H "X-Admin-API-Key: <ADMIN_API_KEY>"
```

PATCH `/documents/{document_id}` accepts only `title`, `content`, `status`, and
`metadata`.

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
VITE_AUTH_MODE=api_key
```

For API-key mode, open `/login`, enter `ADMIN_API_KEY`, and the frontend stores
it in localStorage. Requests to dashboard, calendar, incidents, human review,
technicians, visits, documents, and future audit views send `X-Admin-API-Key`.

For Firebase Auth mode, configure:

```bash
VITE_AUTH_MODE=firebase
VITE_FIREBASE_API_KEY=<web-api-key>
VITE_FIREBASE_AUTH_DOMAIN=<project-id>.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=<project-id>
```

Then open `/login` and sign in with a Firebase email/password user created in
Firebase Console. Requests send `Authorization: Bearer <Firebase ID token>`.
Use the `Salir` button to clear the API key or Firebase session.

Open:

```text
http://127.0.0.1:5173/dashboard
```

The dashboard shows counters for pending and urgent incidents, open human
review items, scheduled visits, visits today, visits this week, and active
technicians. Each card links to its operational section.

Open incidents:

```text
http://127.0.0.1:5173/incidents
```

Open one incident detail:

```text
http://127.0.0.1:5173/incidents/<incident_id>
```

Open the human review queue:

```text
http://127.0.0.1:5173/human-review
```

Open one human review detail:

```text
http://127.0.0.1:5173/human-review/<item_id>
```

The review screen supports filters by status and priority. The detail screen
allows the operator to change status, assign the item, and save resolution notes.

Open technicians:

```text
http://127.0.0.1:5173/technicians
```

Open visits:

```text
http://127.0.0.1:5173/visits
```

Open calendar:

```text
http://127.0.0.1:5173/calendar
```

The calendar supports daily or weekly views, groups visits by day, and filters
by technician and visit status. Clicking a visit opens `/visits/<visit_id>`.
Visit detail includes a `Sincronización calendario` block with provider, event
id, sync status, last sync timestamp, error message, and a manual sync button.

Open documents:

```text
http://127.0.0.1:5173/documents
```

Incident detail can generate an incident summary. Visit detail can generate a
technician brief. Document detail allows title, content, and status edits.

The incident detail screen includes a `Visitas asociadas` block. From there an
operator can create a visit linked to that incident. This is a manual scheduling
action; Hermes does not assign technicians or modify the agenda directly.

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

## Hermes Real Spike

Sprint 10A adds a controlled development spike for real-mode Hermes without
connecting Telegram to a production agent by default.

The technical notes live in:

```text
backend/docs/HERMES_REAL_SPIKE.md
```

Start the fake compatible Hermes endpoint:

```bash
make fake-hermes
```

It listens on:

```text
http://127.0.0.1:9000/agent
```

In another terminal, start the backend in real Hermes mode:

```bash
cd backend
source .venv/bin/activate
HERMES_MODE=real \
HERMES_API_URL=http://127.0.0.1:9000/agent \
uvicorn app.main:app --reload
```

Then run the normalized message smoke test:

```bash
curl -X POST http://127.0.0.1:8000/messages/test \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "telegram",
    "external_user_id": "fake-hermes-user",
    "external_chat_id": "fake-hermes-chat",
    "message_type": "text",
    "text": "Tengo cucarachas en la cocina en Torremolinos desde hace una semana",
    "attachments": [],
    "metadata": {}
  }'
```

Expected result:

- `HermesRealClient` sends a POST request to the fake endpoint.
- The fake endpoint returns a valid `AgentResponse`.
- `/messages/test` returns `action.type=create_incident`.
- A decision record is created with `hermes_mode=real`.

The fake endpoint also supports controlled failure cases by including these
tokens in the message text:

- `fake_invalid_json`
- `fake_invalid_contract`
- `fake_error`
- `fake_timeout`

Those cases should use the safe `escalate_to_human` fallback.

Run the evaluation suite against real mode only when a compatible Hermes endpoint
is configured:

```bash
HERMES_MODE=real HERMES_API_URL=http://127.0.0.1:9000/agent make evals-real
```

The default evaluation command remains mock mode:

```bash
make evals
```

## Hermes Agent Wrapper

Sprint 10B adds a first Hermes Agent wrapper around the same HTTP contract:

```text
POST /agent -> AgentResponse
```

The detailed integration note is:

```text
backend/docs/HERMES_AGENT_INTEGRATION.md
```

Start the wrapper:

```bash
make hermes-agent-server
```

Default wrapper settings:

```bash
HERMES_AGENT_SERVER_PORT=9100
HERMES_SKILLS_DIR=../hermes/skills
HERMES_AGENT_MODE=local
```

The wrapper loads the relevant Markdown skills and validates every output as
`AgentResponse`. In the current repository there is no standalone Hermes runtime
or SDK, so `HERMES_AGENT_MODE=local` is a deterministic local adapter that
exercises the same HTTP boundary safely.

Run evaluations against the wrapper:

```bash
make evals-hermes-agent
```

Equivalent explicit command:

```bash
HERMES_MODE=real \
HERMES_API_URL=http://127.0.0.1:9100/agent \
make evals-real
```

This does not send Telegram messages. The wrapper cannot write directly to
Firestore; only the main backend can persist incidents and decision records
through `ConversationService`.

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

Production behavior:

```bash
APP_ENV=production
```

In production the backend must not silently fall back to mock persistence. If no
Firestore credentials or emulator configuration are present, startup/checks fail
with a clear configuration error.

## Firestore Real Setup

1. Create a Firebase project in Firebase Console.
2. Enable Firestore.
3. Open Project settings > Service accounts.
4. Generate a service account key.
5. Store the JSON outside this repository.
6. Configure `backend/.env`.

Using a local JSON key:

```bash
APP_ENV=development
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_CREDENTIALS_PATH=/absolute/path/outside/repo/firebase-service-account.json
```

Using an environment JSON value:

```bash
APP_ENV=development
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_CREDENTIALS_JSON='{"type":"service_account", "...":"..."}'
```

Run the safe Firestore check:

```bash
make firestore-check
```

The check prints only safe mode/configuration booleans. It never prints
credential file contents, credential JSON, private keys, or tokens.

In mock mode, `make firestore-check` validates the mock persistence path. In real
mode, it creates, reads, updates, and reads a document in:

```text
system_checks
```

Application collections:

```text
conversations
messages
incidents
decision_records
human_review_items
technicians
visits
operational_documents
system_checks
```

With backend using real Firestore, smoke test persistence with:

```bash
curl -X POST http://127.0.0.1:8000/messages/test \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "telegram",
    "external_user_id": "firestore-real-smoke",
    "external_chat_id": "firestore-real-smoke-chat",
    "message_type": "text",
    "text": "Tengo cucarachas en la cocina en Torremolinos desde hace una semana",
    "attachments": [],
    "metadata": {}
  }'

curl http://127.0.0.1:8000/incidents \
  -H "X-Admin-API-Key: <ADMIN_API_KEY>"

curl http://127.0.0.1:8000/audit/decisions \
  -H "X-Admin-API-Key: <ADMIN_API_KEY>"

curl http://127.0.0.1:8000/human-review \
  -H "X-Admin-API-Key: <ADMIN_API_KEY>"
```

Then confirm documents appear in Firebase Console under `conversations`,
`messages`, `incidents`, `decision_records`, and `human_review_items` when the
message requires human review. Manual scheduling creates documents under
`technicians` and `visits`.

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
make evals
make evals-real
make evals-hermes-agent
make fake-hermes
make hermes-agent-server
make firestore-check
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

WhatsApp webhook:

```text
WhatsApp webhook received
IncomingMessage normalized channel=whatsapp external_user_id=... conversation_id=whatsapp:...
ConversationService completed channel=whatsapp external_user_id=... conversation_id=whatsapp:... action_type=create_incident incident_should_create=True
WhatsApp response sent channel=whatsapp external_user_id=... conversation_id=whatsapp:...
```

Hermes:

```text
hermes_request_started hermes_mode=mock
hermes_request_completed hermes_mode=mock action_type=create_incident
hermes_request_started hermes_mode=real
hermes_request_completed hermes_mode=real action_type=create_incident
```

Fallback:

```text
hermes_response_invalid hermes_mode=real
hermes_fallback_used hermes_mode=real
```

Logs must not contain Telegram tokens, WhatsApp access tokens, Hermes API keys,
Firebase credentials, full headers, or unnecessary customer text.

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
