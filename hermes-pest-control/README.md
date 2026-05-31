# Hermes Pest Control System

Hermes Pest Control System is a channel-agnostic backend for pest control operations.
The first planned channel is Telegram, but Telegram is only an adapter. Business logic
works with normalized messages and does not depend on Telegram payloads.

For daily local usage, diagnostics, Telegram E2E testing, and mode switching, see
[OPERATIONS.md](./OPERATIONS.md).

For system boundaries and technical architecture, see
[ARCHITECTURE.md](./ARCHITECTURE.md). For the Hermes agent harness definition
and roadmap, including offline evaluations, see [HARNESS.md](./HARNESS.md).

The first operations panel lives in [frontend](./frontend). It shows generated
incidents at `/incidents` and supports basic status, priority, and internal
notes updates from `/incidents/:id`.

Offline Hermes evaluation cases live in [backend/evals](./backend/evals) and can
be run with `make evals`.

Decision audit records are exposed through `GET /audit/decisions` and documented
in [HARNESS.md](./HARNESS.md).

The operations panel and operational API endpoints support a basic admin API key
guard. Set `REQUIRE_ADMIN_AUTH=true` and `ADMIN_API_KEY` in `backend/.env`, then
log in at `/login` in the frontend.

## Architecture

```text
External channel
  -> ChannelAdapter
  -> IncomingMessage
  -> ConversationService
  -> HermesService
  -> IncidentService / FirestoreService
  -> AgentResponse
```

Core principles:

- Firestore is the future source of truth for business data.
- Hermes Agent proposes actions, but backend services execute them.
- Channel adapters normalize transport-specific payloads.
- Telegram, WhatsApp, webchat, email, and SMS should all converge on the same internal schemas.
- No business workflow belongs inside `TelegramAdapter`.

## Project Layout

```text
hermes-pest-control/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── routes/
│   │   ├── adapters/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── prompts/
│   │   └── config/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── hermes/
│   └── skills/
└── README.md
```

## Install

From the repository root:

```bash
cd hermes-pest-control/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Run Locally

```bash
cd hermes-pest-control/backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

## Test Health

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{
  "status": "ok"
}
```

## Test Normalized Message Intake

```bash
curl -X POST http://127.0.0.1:8000/messages/test \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "telegram",
    "external_user_id": "12345",
    "external_chat_id": "67890",
    "message_type": "text",
    "text": "Tengo cucarachas en la cocina en Torremolinos desde hace una semana",
    "attachments": [],
    "metadata": {}
  }'
```

Expected behavior:

- `action.type` is `create_incident`.
- `incident.pest_type` is `cucarachas`.
- `incident.location` is `Torremolinos`.
- `incident.affected_area` is `cocina`.
- `incident.status` is `pending_review`.

## Running Tests

From the backend directory:

```bash
cd hermes-pest-control/backend
source .venv/bin/activate
python -m pytest
```

The test suite covers:

- Health endpoint behavior.
- Normalized message intake for complete and incomplete pest reports.
- Pydantic validation for channels and agent action types.
- Conversation ID generation.
- Incident creation from an `IncidentDraft`.
- Safe fallback behavior when Hermes returns an invalid response.

## Firebase / Firestore Setup

Firestore is behind `FirestoreService`, so application services do not depend on
Firebase internals. In tests, `APP_ENV=test` uses `MockFirestoreService` and does
not connect to Firebase.

To configure real Firestore:

1. Create a Firebase project in the Firebase Console.
2. Enable Firestore for that project.
3. Create a service account key from Project settings > Service accounts.
4. Download the JSON key outside the repository.
5. Set `FIREBASE_PROJECT_ID` to your Firebase project ID.
6. Set either `FIREBASE_CREDENTIALS_PATH` or `FIREBASE_CREDENTIALS_JSON`.

Using a local JSON file:

```bash
APP_ENV=development
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_CREDENTIALS_PATH=/absolute/path/to/firebase-service-account.json
```

Using JSON from an environment variable:

```bash
APP_ENV=development
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_CREDENTIALS_JSON='{"type":"service_account", "...":"..."}'
```

Using the Firestore emulator:

```bash
APP_ENV=development
USE_FIRESTORE_EMULATOR=true
FIRESTORE_EMULATOR_HOST=127.0.0.1:8080
FIREBASE_PROJECT_ID=demo-hermes-pest-control
```

For automated tests:

```bash
APP_ENV=test
python -m pytest
```

Never commit Firebase credential JSON files. The repository ignores `.env`,
`.env.*`, `*.json`, `firebase-service-account.json`, and `serviceAccountKey.json`.
If a JSON example is ever needed, name it with `.example.json`.

## Hermes Agent Integration

`HermesService` can run in mock mode or real HTTP mode without changing
`TelegramAdapter`, `ConversationService`, or the public API routes.

Modes:

- `HERMES_MODE=mock`: uses `HermesMockClient` and preserves the current deterministic
  sprint behavior.
- `HERMES_MODE=real`: uses `HermesRealClient` and sends a POST request to
  `HERMES_API_URL`.

Environment variables:

```bash
HERMES_MODE=mock
HERMES_API_URL=
HERMES_API_KEY=
HERMES_TIMEOUT_SECONDS=30
```

Recommended request payload sent to Hermes Agent in real mode:

```json
{
  "message": {
    "channel": "telegram",
    "external_user_id": "12345",
    "external_chat_id": "67890",
    "message_type": "text",
    "text": "Tengo cucarachas",
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

Expected response contract:

```json
{
  "reply": "Texto para responder al usuario.",
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
    "summary": "Resumen operativo."
  }
}
```

If Hermes real times out, returns invalid JSON, or does not match `AgentResponse`,
`HermesService` returns a safe `escalate_to_human` fallback and the rest of the
pipeline continues. Logs include the Hermes mode, request lifecycle, invalid
response events, and fallback usage. Logs do not include API keys or full customer
message text.

Telegram works independently of Hermes mode: the same `/webhooks/telegram` route
and `TelegramAdapter` are used whether Hermes is mocked or real.

## Telegram Setup

Telegram is integrated as a channel adapter. `TelegramAdapter` normalizes Telegram
updates into `IncomingMessage` and sends `OutgoingMessage` responses through the
Telegram Bot API. Business logic remains in `ConversationService` and downstream
services.

1. Open Telegram and talk to BotFather.
2. Create a bot with `/newbot`.
3. Copy the token BotFather returns.
4. Create a local `.env` file from `.env.example`.
5. Set `TELEGRAM_BOT_TOKEN`.
6. Optionally set `TELEGRAM_WEBHOOK_SECRET` to validate Telegram's
   `X-Telegram-Bot-Api-Secret-Token` header.
7. Start FastAPI locally.
8. Expose local port `8000` with ngrok or Cloudflare Tunnel.
9. Configure the Telegram webhook.
10. Check webhook info.
11. Send a message to the bot and watch backend logs.

Example `.env` values:

```bash
APP_ENV=development
TELEGRAM_BOT_TOKEN=123456:your-bot-token
TELEGRAM_WEBHOOK_SECRET=choose-a-long-random-secret
TELEGRAM_WEBHOOK_URL=https://your-public-url.example.com/webhooks/telegram
TELEGRAM_INTERNAL_ALERT_CHAT_ID=
```

Run locally:

```bash
cd hermes-pest-control/backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

Expose local port `8000` with ngrok:

```bash
ngrok http 8000
```

Or with Cloudflare Tunnel:

```bash
cloudflared tunnel --url http://127.0.0.1:8000
```

Configure the webhook directly with Telegram:

```bash
curl "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook?url=<PUBLIC_URL>/webhooks/telegram"
```

If using `TELEGRAM_WEBHOOK_SECRET`, include it when setting the webhook:

```bash
curl -X POST "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "<PUBLIC_URL>/webhooks/telegram",
    "secret_token": "<TELEGRAM_WEBHOOK_SECRET>"
  }'
```

The backend also provides a helper endpoint. It uses `TELEGRAM_BOT_TOKEN` and, if
configured, `TELEGRAM_WEBHOOK_SECRET`:

```bash
curl -X POST http://127.0.0.1:8000/telegram/set-webhook \
  -H "Content-Type: application/json" \
  -d '{"webhook_url": "<PUBLIC_URL>/webhooks/telegram"}'
```

There is also an optional script:

```bash
cd hermes-pest-control/backend
source .venv/bin/activate
python scripts/set_telegram_webhook.py
```

And webhook info:

```bash
curl http://127.0.0.1:8000/telegram/webhook-info
```

You can also query Telegram directly:

```bash
curl "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getWebhookInfo"
```

For local tests, no Telegram token is required. Without `TELEGRAM_BOT_TOKEN`, the
application still starts, but real Telegram send/configuration calls return a
clear configuration error.

## Manual Telegram E2E Test

This test keeps `HermesService` mocked. If no Firebase credentials are configured
in development, persistence uses `MockFirestoreService`.

1. Configure `.env` with `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_URL`, and optional
   `TELEGRAM_WEBHOOK_SECRET`.
2. Start the backend:

```bash
cd hermes-pest-control/backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

3. Start ngrok or Cloudflare Tunnel and set `TELEGRAM_WEBHOOK_URL` to:

```text
https://<PUBLIC_URL>/webhooks/telegram
```

4. Configure the webhook:

```bash
python scripts/set_telegram_webhook.py
```

5. Confirm webhook info:

```bash
curl http://127.0.0.1:8000/telegram/webhook-info
```

6. Send this exact message to the Telegram bot:

```text
Tengo cucarachas en la cocina en Torremolinos desde hace una semana
```

Expected bot response begins with:

```text
Gracias por la información. He registrado el aviso para que el equipo lo revise...
```

Expected backend logs include:

```text
Telegram webhook received
IncomingMessage normalized
ConversationService completed
```

The structured log fields should show:

- `channel=telegram`
- `external_user_id=<telegram user id>`
- `conversation_id=telegram:<telegram user id>`
- `action_type=create_incident`
- `incident_should_create=True`

Logs intentionally do not include Telegram tokens, Firebase credentials, full
headers, or unnecessary personal data.

## Docker

```bash
cd hermes-pest-control/backend
docker build -t hermes-pest-control-backend .
docker run --rm -p 8000:8000 hermes-pest-control-backend
```

## Next Sprint

Recommended next steps:

1. Validate the Telegram webhook against a staging bot and public HTTPS tunnel.
2. Replace the mock `HermesService` with a real Hermes integration behind the same service contract.
3. Add persisted clients and richer incident lifecycle transitions.
4. Add WhatsApp, webchat, email, or SMS adapters behind the existing channel contract.
5. Expand operational monitoring, retries, and alerting for failed outbound messages.
