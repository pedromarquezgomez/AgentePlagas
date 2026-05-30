# Hermes Pest Control System

Hermes Pest Control System is a channel-agnostic backend for pest control operations.
The first planned channel is Telegram, but Telegram is only an adapter. Business logic
works with normalized messages and does not depend on Telegram payloads.

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

## Docker

```bash
cd hermes-pest-control/backend
docker build -t hermes-pest-control-backend .
docker run --rm -p 8000:8000 hermes-pest-control-backend
```

## Next Sprint

Recommended next steps:

1. Add real Telegram webhook routing while keeping Telegram inside `TelegramAdapter`.
2. Replace the mock `HermesService` with a real Hermes integration behind the same service contract.
3. Connect `FirestoreService` to Firebase Admin SDK.
4. Add persisted conversations, clients, and incident lifecycle transitions.
5. Add authentication and signature validation for external channel webhooks.
6. Add tests for adapters, conversation orchestration, and incident creation.

