# Hermes Pest Control System Architecture

## Purpose

Hermes Pest Control System is a channel-agnostic operational backend for pest
control intake. The system receives customer messages, normalizes them into
internal schemas, asks Hermes for an operational decision, persists the relevant
conversation data, and exposes incidents to a minimal operations panel.

The current product surface is intentionally small:

- Telegram webhook integration.
- Optional WhatsApp webhook integration.
- Mock or real-ready Hermes service.
- Mock or Firestore-ready persistence.
- Incidents API.
- Minimal Vue operations panel.
- Manual technician and visit management.
- Optional manual Google Calendar synchronization for visits.
- Basic internal operational documents.

## Architectural Principles

- Channel adapters do transport work only.
- ConversationService orchestrates the application flow.
- HermesService is replaceable and hides mock/real runtime provider selection.
- Business services execute decisions; the agent proposes actions.
- Persistence services are infrastructure, not domain logic.
- Firestore/VisitService remains the source of truth for visits; Google Calendar
  is only an optional external projection.
- Schemas validate the boundary between layers.
- Error paths must fail safely and avoid leaking secrets.

## Runtime Flow

```text
External channel API (Telegram or WhatsApp)
  -> POST /webhooks/{channel}
  -> ChannelAdapter.parse_incoming
  -> IncomingMessage
  -> ConversationService.handle_incoming_message
  -> HermesService.process_message
  -> AgentResponse
  -> IncidentService.create_incident when required
  -> DecisionAuditService.create_decision_record
  -> FirestoreService or MockFirestoreService
  -> OutgoingMessage
  -> ChannelAdapter.send_message
  -> External channel API
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
message metadata, and photo attachments. `WhatsAppAdapter` supports Meta
WhatsApp text payloads, phone/user ids, message metadata, and basic media
attachment metadata. Adapters do not decide whether an incident should be
created.

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

HermesService is the agent boundary. It selects a neutral runtime provider using
`HERMES_MODE` and returns an AgentResponse. If the real provider fails or
returns an invalid response, HermesService returns a safe `escalate_to_human`
fallback.

Current modes:

- `AGENT_PROVIDER=llm`: primary standard LLM runtime provider.
- `AGENT_PROVIDER=mock`: deterministic local/test behavior.
- `AGENT_PROVIDER=nous_hermes`: experimental HTTP runtime provider for
  Hermes/Nous-compatible wrappers.

When `AGENT_PROVIDER=llm` is enabled, the LLM becomes the primary response
generator, but it still runs inside the harness. It receives
`ConversationContext`, product skills, backend tool metadata, and
`PolicyEngine` constraints. It may propose an `AgentResponse` and actions such
as `create_incident`, but it cannot write to Firestore, execute tools, send
messages, send email, or create calendar events. Any real action still flows
through:

```text
AgentResponse
  -> ConversationService
  -> PolicyEngine
  -> ToolExecutionService
  -> Domain Service
  -> Firestore
```

If the LLM request times out, the provider API fails, or the response cannot be
validated as `AgentResponse`, `LLMRuntimeProvider` falls back to
`MockAgentRuntimeProvider` and annotates the response metadata with
`fallback_used`, `fallback_reason`, and `fallback_provider=mock`.

Temporary compatibility remains:

- `HERMES_MODE=mock`: maps to the mock provider when `AGENT_PROVIDER` is unset.
- `HERMES_MODE=real`: maps to the experimental `nous_hermes` provider when
  `AGENT_PROVIDER` is unset.

Runtime abstractions live under `backend/app/harness/`:

- `runtime.py`: provider protocol and legacy-client compatibility adapter.
- `contracts.py`: neutral `AgentRuntimeRequest` passed to providers.
- `providers/llm_provider.py`: primary standard LLM provider.
- `providers/mock_provider.py`: deterministic provider for local/test behavior.
- `providers/hermes_http_provider.py`: experimental HTTP provider for
  Hermes/Nous-compatible wrappers.

`ConversationService` depends on `HermesService`, not on Hermes Agent, Nous,
HTTP endpoints, skills, or wrapper internals. Hermes Agent is therefore an
optional provider behind the same AgentResponse contract. Firestore remains the
source of truth, and agents only propose responses/actions; backend services
perform persistence and controlled execution.

The architectural core is the Hermes Pest Harness: schemas, orchestration,
decision audit, human review, tool review, and backend business services. Runtime
providers are replaceable inference adapters behind that harness.

### Context Manager Layer

Location: `backend/app/context/`

The Context Manager Layer decouples the preparation of the business context from the runtime providers. 
Instead of providers collecting and formatting context information individually, the orchestration layer relies on `ContextManager` to build a unified `ConversationContext`.

This layer includes specialized builders:
- `HistoryBuilder` (loads past conversation history from Firestore or parameters).
- `IncidentBuilder` (queries Firestore for active/pending incidents to resume intake).
- `SkillsBuilder` (retrieves the active product skills from registry).
- `ToolsBuilder` (retrieves the available tools from registry).

It also queries `PolicyEngine` to populate `policy_constraints` for the target provider. Providers receive the resulting `ConversationContext` unchangeably.

### Product Skills

Location: `backend/app/skills/`


Skills are product-owned capability definitions, not Nous/Hermes Agent
framework assets. The neutral `SkillRegistry` exposes declarative skills such
as:

- `classify_pest`;
- `request_missing_info`;
- `create_incident`;
- `escalate_to_human`;
- `suggest_visit`;
- `summarize_case`.

Runtime providers receive the available skills through `AgentRuntimeRequest`.
Providers may use them to structure replies or proposed actions, but skills do
not execute side effects. Firestore writes, incident creation, visits,
documents, messages, and tools remain controlled by backend services.

Legacy markdown files under `hermes/skills` may still be used by the
experimental HTTP wrapper while it is migrated, but they are no longer the
architectural source of product capability definitions.

### Backend Tools

Location: `backend/app/tools/`

Tools are backend-owned technical actions. A skill describes what Hermes Pest
can reason about; a tool describes how the backend may execute a concrete
operation through an existing service.

Initial tools:

- `create_incident_tool` -> `IncidentService`;
- `get_incident_tool` -> `IncidentService`;
- `list_incidents_tool` -> `IncidentService`;
- `escalate_to_human_tool` -> `HumanReviewService`;
- `suggest_visit_tool` -> `VisitService`.

`ToolRegistry` exposes tool metadata to providers through `AgentRuntimeRequest`,
but providers are forbidden callers. Providers can only propose intent or
structured actions. Actual state changes remain with services such as
IncidentService, HumanReviewService, VisitService, and ToolExecutionService.

#### Tool Execution Lifecycle

Location: `backend/app/tools/execution_contracts.py`

All current and future tool executions share an internal lifecycle contract:

```text
ToolExecutionRequest -> ToolExecutionResult | ToolExecutionError
```

The formal statuses are:

```text
PENDING -> APPROVED -> EXECUTED
PENDING -> DENIED
PENDING -> REQUIRES_HUMAN_REVIEW
PENDING -> APPROVED -> FAILED
```

`ToolExecutionRequest` captures what tool is being requested, who or what
provider requested it, and the payload proposed for execution. `ToolExecution`
results and errors standardize successful execution and failure reporting.
Public API records remain backward compatible, but the service layer now has a
single internal contract for execution lifecycle, audit preparation, and future
tool integrations.

#### Harness Audit Log

Location: `backend/app/audit/`

The Harness Audit Log records the important control-plane events around tool
execution:

```text
Provider -> Skill -> Tool -> PolicyEngine -> ToolExecutionService -> Resultado
```

Current audit storage is in-memory only. It is designed for structured
traceability and tests, not yet for analytics or long-term persistence. Audit
events record tool proposal, policy evaluation, human review routing, execution
start, execution completion, and execution failure.

Responsibilities remain separate:

```text
Provider = razona
Skill = define capacidad
PolicyEngine = autoriza
ToolExecutionService = ejecuta
AuditService = registra
```

`AuditService` is best-effort. If audit storage fails, the operational path must
continue so that audit outages do not block approved tool execution or safety
fallbacks.

The boundary is:

```text
Skill = what Hermes Pest knows how to reason about.
Tool = technical backend action available under policy.
Policy Engine = authorization decision for proposed tool/action.
Provider = model/runtime that proposes responses or actions.
Service = backend owner that modifies real state.
```

### Policy Engine

Location: `backend/app/policies/`

The Policy Engine is the governance layer of the Agent Harness. Providers may
reason and propose actions, but they do not authorize execution. Skills describe
business capabilities, but they do not authorize execution either. Backend
services perform real state changes, but the authorization decision belongs to
the harness policy layer before a tool is executed.

Initial decisions:

- `create_incident_tool` -> `ALLOW`;
- `get_incident_tool` -> `ALLOW`;
- `list_incidents_tool` -> `ALLOW`;
- `escalate_to_human_tool` -> `ALLOW`;
- `suggest_visit_tool` -> `REQUIRE_HUMAN_REVIEW`;
- unknown tools -> `DENY`.

The current controlled Gmail draft execution path is also evaluated by the
Policy Engine before delegating to `ToolExecutionService`. `gmail.send_email`
remains denied because it is not an allowed policy rule.

#### Policy Enforcement Boundary

Controlled tool execution has a single production entry point:

```text
Route /tools/executions/{id}/execute
-> PolicyEngine
-> ToolExecutionService
-> controlled backend executor/service
```

Providers, skills, and registries are not execution layers. Providers may
propose structured actions, skills describe product capabilities, and registries
publish metadata. They must not call backend services, Gmail executors,
Firestore, or `execute_execution_record` directly. This boundary keeps the
final authorization decision inside the harness, not inside an LLM provider or
experimental agent runtime.

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

### SLA Monitoring

Location: `backend/app/incidents/sla/`

SLA monitoring is a dynamic domain calculation. The system persists only the
incident creation time, current incident status, and assigned `sla_hours`.
`SLAEngine` computes the live status on read:

```text
ON_TRACK
AT_RISK
BREACHED
COMPLETED
```

No cron job, worker, queue, or scheduler is required for the current phase.
The API exposes calculated fields such as `sla_status`, `elapsed_hours`,
`remaining_hours`, and `breach_hours`. The first transition observed as
`BREACHED` records an `INCIDENT_SLA_BREACHED` audit event and marks only that
the breach was audited, not the SLA state itself.

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
manual create, list, detail, controlled updates, and date-range reads for the
internal calendar. There is no route optimization and no agent-driven
assignment.

Google Calendar synchronization is an optional projection invoked explicitly
through `POST /visits/{visit_id}/sync-calendar`. Sync writes only external
calendar metadata back to the visit; it does not make Google Calendar the source
of truth.

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
- `operational_documents`;
- `system_checks`.

### OperationalDocumentService

Location: `backend/app/services/operational_document_service.py`

OperationalDocumentService owns basic internal document drafts associated with
incidents or visits. It supports create, list, detail, and controlled updates.
Template generation uses persisted incident/visit data. Hermes cannot create
documents directly.

PATCH allows only:

- `title`;
- `content`;
- `status`;
- `metadata`.

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
- `POST /visits/{visit_id}/sync-calendar`
- `GET /calendar/visits`
- `GET /documents`
- `POST /documents`
- `GET /documents/{document_id}`
- `PATCH /documents/{document_id}`
- `POST /incidents/{incident_id}/generate-summary-document`
- `POST /visits/{visit_id}/generate-technician-brief`
- `POST /messages/test`
- `POST /webhooks/telegram`
- `GET /webhooks/whatsapp`
- `POST /webhooks/whatsapp`
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
- `/calendar`: internal day/week agenda grouped by date with technician/status
  filters.
- `/documents`: table, filters, loading/error/empty states.
- `/documents/:id`: editable title/content/status form.

## Security Posture

Current safeguards:

- Telegram bot token, WhatsApp access token, webhook secrets, Hermes API key,
  and Firebase credentials are read from environment settings.
- `/config/status` reports booleans and modes, not secret values.
- Telegram webhook secret is validated when configured.
- WhatsApp verification and optional webhook secret are validated when
  configured.
- Logs avoid full headers, tokens, API keys, and full customer text.
- CORS is restricted to local Vite origins for development.
- PATCH routes use Pydantic schemas with `extra="forbid"`.
- Operational endpoints can be protected with `AUTH_MODE=api_key` plus
  `REQUIRE_ADMIN_AUTH=true`, or with `AUTH_MODE=firebase` and Firebase ID-token
  verification.
- `AUTH_MODE=disabled` is allowed only outside production.
- Human review, technician, visit, calendar, dashboard, audit, document, and
  incident endpoints share the same admin-user dependency.
- Google Calendar sync is disabled by default and uses service-account
  credentials only when explicitly configured.
- Hermes cannot directly assign technicians, create visits, or update agenda
  records, cannot invoke Google Calendar sync directly, and cannot create
  operational documents directly.
- The frontend supports API-key login and Firebase email/password login.

Known limitations:

- Firebase Auth currently identifies users but does not enforce roles or
  multi-company permissions.
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
