# Hermes Pest Control System Architecture

## Purpose

Hermes Pest Control System is a channel-agnostic operational backend for pest
control intake. The system receives customer messages, normalizes them into
internal schemas, asks Hermes for an operational decision, persists the relevant
conversation data, and exposes incidents to a minimal operations panel.

The current product surface is intentionally small:

- Telegram webhook integration.
- Mock or real-ready Hermes service.
- Mock or Firestore-ready persistence.
- Incidents API.
- Minimal Vue operations panel.
- Manual technician and visit management.

## Architectural Principles

- Channel adapters do transport work only.
- ConversationService orchestrates the application flow.
- HermesService is replaceable and hides mock/real client selection.
- Business services execute decisions; the agent proposes actions.
- Persistence services are infrastructure, not domain logic.
- Schemas validate the boundary between layers.
- Error paths must fail safely and avoid leaking secrets.

## Runtime Flow

```text
Telegram Bot API
  -> POST /webhooks/telegram
  -> TelegramAdapter.parse_incoming
  -> IncomingMessage
  -> ConversationService.handle_incoming_message
  -> HermesService.process_message
  -> AgentResponse
  -> IncidentService.create_incident when required
  -> DecisionAuditService.create_decision_record
  -> FirestoreService or MockFirestoreService
  -> OutgoingMessage
  -> TelegramAdapter.send_message
  -> Telegram Bot API
```

The local test endpoint follows the same internal flow after constructing an
IncomingMessage:

```text
POST /messages/test
  -> IncomingMessage
  -> ConversationService
  -> HermesService
  -> IncidentService / persistence
  -> DecisionAuditService / persistence
  -> AgentResponse
```

The operations panel reads and updates incidents through the public backend API:

```text
Vue panel
  -> GET /incidents
  -> GET /incidents/{incident_id}
  -> PATCH /incidents/{incident_id}
  -> IncidentService
  -> FirestoreService or MockFirestoreService
```

## Main Components

### Channel Adapters

Location: `backend/app/adapters/`

Adapters convert external payloads into internal messages and send outbound
responses. `TelegramAdapter` currently supports text, captions, chat/user ids,
message metadata, and photo attachments. It does not decide whether an incident
should be created.

### Schemas

Location: `backend/app/schemas/`

Important schemas:

- `IncomingMessage`: normalized inbound channel message.
- `OutgoingMessage`: normalized outbound channel response.
- `AgentResponse`: contract returned by Hermes.
- `IncidentDraft`: data required to create an incident.
- `Incident`: persisted operational incident.
- `IncidentUpdate`: controlled update contract for PATCH.

`IncidentUpdate` forbids unknown fields, so PATCH cannot update arbitrary
incident data.

### ConversationService

Location: `backend/app/services/conversation_service.py`

ConversationService is the orchestrator. It:

- builds `conversation_id` as `channel:external_user_id`;
- upserts the conversation;
- stores inbound and outbound messages;
- calls HermesService;
- converts actionable AgentResponse data into IncidentDraft;
- delegates incident creation to IncidentService;
- records structured decision audit entries through DecisionAuditService;
- creates human review items through HumanReviewService when decisions require
  operator attention.

It does not assign technicians or modify the agenda from Hermes output.

### HermesService

Location: `backend/app/services/hermes_service.py`

HermesService is the agent boundary. It selects a mock or real-ready client
using `HERMES_MODE` and returns an AgentResponse. If the real client fails or
returns an invalid response, HermesService returns a safe
`escalate_to_human` fallback.

Current modes:

- `HERMES_MODE=mock`: deterministic local behavior.
- `HERMES_MODE=real`: HTTP client prepared for Hermes Agent.

Sprint 10A adds a development-only fake Hermes HTTP server at
`backend/scripts/fake_hermes_server.py`. It is not part of the production
runtime; it exists to verify the real-mode HTTP boundary, response validation,
timeouts, invalid responses, and fallback behavior without Telegram traffic.

Sprint 10B adds `backend/scripts/hermes_agent_server.py`, a first Hermes Agent
wrapper. It loads the project skills, exposes the same `POST /agent` contract,
and validates all outputs as `AgentResponse`. The wrapper is outside the
business backend and has no direct persistence or Telegram-send permissions.

### IncidentService

Location: `backend/app/services/incident_service.py`

IncidentService owns incident lifecycle operations:

- create incident from IncidentDraft;
- list incidents;
- get incident detail;
- update controlled operational fields.

PATCH allows only:

- `status`;
- `priority`;
- `internal_notes`.

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

### DecisionAuditService

Location: `backend/app/services/decision_audit_service.py`

DecisionAuditService owns structured records of Hermes decisions. It stores
records in the `decision_records` collection using the same Firestore-compatible
persistence layer as conversations, messages, and incidents.

Each decision record captures:

- `trace_id`;
- `conversation_id`;
- optional `message_id`;
- optional `incident_id`;
- channel;
- Hermes mode;
- action type;
- incident creation intent;
- pest type and priority when available;
- fallback status and reason;
- prompt, skill, and response-contract versions;
- safe metadata.

The service does not decide business behavior. It only records decisions already
made by the orchestrated flow.

### HumanReviewService

Location: `backend/app/services/human_review_service.py`

HumanReviewService owns the operator review queue. It stores items in
`human_review_items` after `ConversationService` detects one of these conditions:

- Hermes requested `escalate_to_human`;
- safe fallback was used;
- priority is `urgent`;
- response metadata marks the case as sensitive.

The service supports create, list, detail, and controlled updates. PATCH accepts
only `status`, `assigned_to`, and `resolution_notes`; it does not allow free-form
editing of decision, incident, or trace fields.

### TechnicianService

Location: `backend/app/services/technician_service.py`

TechnicianService owns manual technician records. It supports create, list,
detail, and controlled updates. Hermes has no write path to this service.

PATCH allows only:

- `name`;
- `phone`;
- `email`;
- `active`;
- `service_area`;
- `skills`.

### VisitService

Location: `backend/app/services/visit_service.py`

VisitService owns basic agenda entries associated with incidents. It supports
manual create, list, detail, and controlled updates. There is no route
optimization, no Google Calendar integration, and no agent-driven assignment.

PATCH allows only:

- `technician_id`;
- `scheduled_start`;
- `scheduled_end`;
- `status`;
- `address`;
- `notes`.

### Persistence

Location: `backend/app/services/firestore_service.py` and
`backend/app/services/mock_firestore_service.py`

Persistence is abstracted behind FirestoreService-compatible methods. The mock
implementation is shared in test/development mode so different route services
see the same local data during a process lifetime.

FirestoreService contains infrastructure behavior only: create, get, update,
list, and append to subcollection. It does not know pest-control business rules.

Persistence mode is selected by `backend/app/services/firestore_factory.py`:

- `APP_ENV=test`: always `MockFirestoreService`.
- `APP_ENV=development` without credentials: `MockFirestoreService`.
- `APP_ENV=development` with credentials or emulator: `FirestoreService`.
- `APP_ENV=production` without credentials: explicit configuration error.

Runtime Firestore collections:

- `conversations`;
- `messages`;
- `incidents`;
- `decision_records`;
- `human_review_items`;
- `technicians`;
- `visits`;
- `system_checks`.

### API Routes

Location: `backend/app/routes/`

Current operational routes:

- `GET /health`
- `GET /config/status`
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
- `POST /messages/test`
- `POST /webhooks/telegram`
- `POST /telegram/set-webhook`
- `GET /telegram/webhook-info`
- `GET /incidents`
- `GET /incidents/{incident_id}`
- `PATCH /incidents/{incident_id}`

Separate development agent servers:

- `backend/scripts/fake_hermes_server.py`: contract fake from Sprint 10A.
- `backend/scripts/hermes_agent_server.py`: skill-loading wrapper from Sprint
  10B.

### Frontend

Location: `frontend/`

The frontend is a minimal Vue 3 + TypeScript + Vite operations panel. It uses
the backend API through `src/services/api.ts` and does not access persistence or
agent internals directly.

Current screens:

- `/incidents`: table, filters, loading/error/empty states.
- `/incidents/:id`: detail, status/priority/internal-notes edit form, save
  feedback.
- `/human-review`: table, filters, loading/error/empty states.
- `/human-review/:id`: detail, status/assigned-to/resolution-notes edit form,
  save feedback.
- `/technicians`: table, filters, loading/error/empty states, create action.
- `/technicians/:id`: create/detail form for technician profile.
- `/visits`: table, filters, loading/error/empty states, create action.
- `/visits/:id`: create/detail form for visit scheduling.

## Security Posture

Current safeguards:

- Telegram bot token, webhook secret, Hermes API key, and Firebase credentials
  are read from environment settings.
- `/config/status` reports booleans and modes, not secret values.
- Telegram webhook secret is validated when configured.
- Logs avoid full headers, tokens, API keys, and full customer text.
- CORS is restricted to local Vite origins for development.
- PATCH routes use Pydantic schemas with `extra="forbid"`.
- Operational incident and audit endpoints can be protected with
  `REQUIRE_ADMIN_AUTH=true` and `X-Admin-API-Key`.
- Human review queue endpoints use the same admin API-key protection.
- Technician and visit endpoints use the same admin API-key protection.
- Hermes cannot directly assign technicians, create visits, or update agenda
  records.
- The frontend has a minimal API-key login screen prepared to evolve toward
  Firebase Auth.

Known limitations:

- The current panel login is a simple shared API-key guard, not user-level auth.
- CORS settings are development-oriented.
- Internal notes are plain text and should be treated as sensitive operational
  data once real users are added.

## Testing Strategy

Backend tests cover:

- health endpoint;
- message test endpoint;
- schema validation;
- ConversationService orchestration;
- IncidentService;
- Firestore mock behavior;
- config status;
- Telegram adapter/webhook behavior;
- Hermes mock/real/fallback behavior;
- Hermes real-mode fake endpoint/client behavior;
- Hermes Agent wrapper contract behavior;
- decision records and audit routes;
- human review service and routes;
- technician and visit service/routes;
- incidents list/detail/update routes.

Frontend currently relies on TypeScript/Vite build verification and manual smoke
testing. Automated frontend component or E2E tests are intentionally deferred.

## Review Status

As of Sprint 6.5, the architecture remains correctly separated for the current
scope. No critical architecture issue was found in the reviewed code.
