# Agent Harness

## What Agent Harness Means Here

An agent harness is the operational frame around an AI agent. It is not only the
model call. It includes the contracts, adapters, validation, tools, persistence,
fallbacks, observability, tests, and human controls that make an agent safe and
useful inside a real business workflow.

For Hermes Pest Control System, the harness is the layer that lets Hermes reason
about pest-control conversations while the backend keeps control over:

- what data enters the agent;
- what shape the agent response must have;
- which actions are allowed;
- how incidents are persisted;
- how failures are escalated;
- how operators review outcomes.

## Current Harness Inventory

### Channel Adapters

Implemented:

- `BaseChannelAdapter`
- `TelegramAdapter`
- `WhatsAppAdapter`
- placeholder adapters for webchat and email

Role in the harness:

- normalize external channel payloads;
- hide transport-specific details;
- send responses without business decisions.

WhatsApp is treated as a second channel, not a separate business flow. Its
adapter maps Meta webhook payloads into `IncomingMessage`, while
`ConversationService`, Hermes validation, incident creation, decision records,
and human review behavior stay shared with Telegram.

### Message Contracts

Implemented:

- `IncomingMessage`
- `OutgoingMessage`

Role in the harness:

- stable input and output format for all channels;
- consistent message metadata and attachment handling.

### Agent Response Contract

Implemented:

- `AgentResponse`
- `AgentAction`
- `AgentIncidentProposal`

Role in the harness:

- constrains Hermes output;
- limits valid action types to known operational actions;
- enables backend validation before acting.

### Pydantic Validation

Implemented across:

- incoming messages;
- outgoing messages;
- agent response;
- incidents;
- incident updates.

Role in the harness:

- rejects invalid channel or agent data early;
- makes fallback behavior predictable;
- prevents arbitrary update payloads in incident management.

### Hermes Mock and Real-Ready Clients

Implemented:

- `HermesMockClient`
- `HermesRealClient`
- `HermesService`

Role in the harness:

- deterministic local tests in mock mode;
- HTTP boundary prepared for the real Hermes Agent;
- same public service method regardless of mode.

### Safe Fallback

Implemented:

- invalid Hermes responses fall back to `escalate_to_human`;
- timeout or HTTP failure in real mode falls back safely;
- fallback incident proposal is created for review.

Role in the harness:

- protects the user experience;
- keeps operational continuity;
- avoids silent loss of important customer messages.

### Business Services

Implemented:

- `ConversationService`
- `IncidentService`
- persistence services

Role in the harness:

- ConversationService orchestrates;
- IncidentService executes incident lifecycle behavior;
- persistence services store data without domain-specific branching.

### Context Manager

Implemented:

- `ConversationContext`
- `ContextManager`
- `HistoryBuilder`
- `IncidentBuilder`
- `SkillsBuilder`
- `ToolsBuilder`

Role in the harness:

- isolates business context construction from the providers;
- loads recent conversation history and active incidents from Firestore;
- queries active skills and tools registries;
- maps `PolicyEngine` rules into `policy_constraints`;
- provides an unchangeable input context to the provider layer.

### Logging and Diagnostics

Implemented:

- Telegram webhook lifecycle logs;
- WhatsApp webhook lifecycle logs;
- normalized message metadata logs without full customer text;
- Hermes request/fallback logs;
- `/config/status` safe configuration endpoint;
- operational scripts and smoke tests.

Role in the harness:

- allows local diagnosis;
- confirms mode selection;
- avoids exposing tokens or API keys.

### Tests

Implemented:

- backend pytest suite;
- route tests;
- schema tests;
- service tests;
- Telegram adapter/webhook tests;
- WhatsApp adapter/webhook tests;
- Hermes mode/fallback tests;
- incident management tests.

Role in the harness:

- keeps contracts stable;
- protects channel/agent/business boundaries;
- verifies safe failure behavior.

### Operations Panel

Implemented:

- incidents list;
- filters;
- incident detail;
- controlled status/priority/internal-notes update.

Role in the harness:

- gives humans visibility over agent-created work;
- creates the first review surface before richer workflows exist.

### Evaluation Harness

Implemented:

- JSON-based evaluation cases in `backend/evals/cases`;
- offline runner in `backend/evals/run_evals.py`;
- `make evals` command;
- optional JSON result export;
- pass/fail reporting by case;
- trace fields per case result.

Problem it solves:

- catches regressions in Hermes decisions before using Hermes real;
- documents expected behavior for pest-intake, escalation, and safety cases;
- verifies response-contract behavior without sending Telegram messages;
- gives the team a lightweight replay-style loop for prompt and agent changes.

How to run it:

```bash
make evals
```

Or from `backend`:

```bash
python -m evals.run_evals
python -m evals.run_evals --output evals/results/latest.json
```

What it measures now:

- expected `action_type`;
- expected incident proposal fields;
- expected `missing_fields`;
- required reply substrings;
- forbidden reply substrings;
- per-case pass/fail status.

Mode scoping:

- cases without `hermes_modes` apply to both `mock` and `real`;
- cases with `"hermes_modes": ["real"]` are LLM-candidate policy checks and do
  not affect `make evals` in the current mock production baseline;
- this lets product policy mature before any Pilot Mode activation.

Product-policy reference:

```text
backend/docs/HERMES_PRODUCT_POLICY.md
```

### Synthetic Evaluation Generator

Implemented:

- deterministic template generator in `backend/evals/synthetic/generate_synthetic_cases.py`;
- optional LLM case generation behind `SYNTHETIC_GENERATION_MODE=llm`;
- local synthetic shadow runner in `backend/evals/synthetic/run_synthetic_shadow_eval.py`;
- manual promotion helper in `backend/evals/synthetic/promote_cases_to_evals.py`;
- `make synthetic-cases`;
- `make synthetic-shadow-eval`;
- explicit controlled command `make synthetic-shadow-eval-cloud`.

Role in the harness:

- generates broader pest-control intake coverage without Telegram;
- compares the active mock decision against a shadow LLM decision;
- produces aggregate mismatch and fallback metrics;
- marks synthetic messages in metadata;
- keeps prompt/skill changes human-reviewed instead of automatic.

Safety boundaries:

- no Telegram or WhatsApp messages are sent;
- production is not touched by default;
- Firestore real is avoided by default;
- OpenAI is not called in tests;
- generated reports are diagnostic, not self-training instructions.

Full runbook:

```text
backend/docs/SYNTHETIC_EVALUATION.md
```

Traceability fields generated now:

- `eval_run_id`;
- `case_id`;
- `trace_id`;
- `hermes_mode`;
- `action_type`;
- `incident_should_create`;
- `pest_type`;
- `priority`;
- `fallback_used`;
- `fallback_reason`;
- `response_contract_version`;
- `passed`;
- `failure_reasons`.

Current limitations:

- evaluations are single-turn only;
- results are not persisted to Firestore;
- no prompt version is recorded yet;
- no scoring beyond rule-based checks;
- no frontend report UI;
- real Hermes mode is wired but should not be used for production gating until
  the API contract is finalized.

Real-mode spike:

- `make fake-hermes` starts a local HTTP endpoint compatible with
  `HermesRealClient`;
- `make evals-real` can run the same evaluation runner with
  `HERMES_MODE=real`;
- the fake endpoint supports valid responses, invalid JSON, invalid
  `AgentResponse`, HTTP error, and timeout simulations;
- Telegram is not required and no channel messages are sent during these tests.

Hermes Agent wrapper:

- `make hermes-agent-server` starts the Sprint 10B wrapper on port `9100`;
- the wrapper loads the pest-control skills from `hermes/skills`;
- it exposes the same `POST /agent` contract consumed by `HermesRealClient`;
- it validates all outputs as `AgentResponse`;
- `make evals-hermes-agent` runs the evaluation harness against this wrapper.

LLM Agent mode:

- `HERMES_AGENT_MODE=llm` keeps the LLM behind the same `/agent` HTTP wrapper;
- `ConversationService`, channel adapters, Firestore services, and Telegram do
  not call the LLM directly;
- `make hermes-agent-llm` starts the wrapper in LLM mode;
- `make evals-agent-llm` runs dry-run evals through `HermesRealClient` without
  sending channel messages;
- outputs must validate as `AgentResponse` or the backend falls back safely.

Next steps:

- add multi-turn conversation cases;
- add prompt and schema version metadata;
- add replay from stored conversations;
- add quality metrics over repeated runs;
- add a curated Spanish pest-control dataset;
- separate smoke cases from safety/regression gates if the suite grows.

### Hermes Real Spike

Implemented for Sprint 10A:

- `HermesRealClient` sends the normalized `IncomingMessage`, conversation
  history, business context, and response-contract marker to an HTTP endpoint;
- responses are accepted only if they validate as `AgentResponse`;
- invalid JSON, invalid contracts, HTTP errors, and timeouts raise controlled
  client errors;
- `HermesService` catches those errors and returns the existing safe fallback;
- `backend/scripts/fake_hermes_server.py` provides a development-only compatible
  endpoint for smoke testing real mode;
- `/config/status` reports whether `HERMES_API_URL` and `HERMES_API_KEY` are
  configured without exposing their values.

Recommended integration shape:

- keep Hermes behind an HTTP boundary;
- keep `ConversationService` as the orchestrator;
- keep channel adapters independent of Hermes mode;
- use `/messages/test`, evals, and replay tooling before connecting a real agent
  to Telegram traffic.

The full spike note is in `backend/docs/HERMES_REAL_SPIKE.md`.

### Hermes Agent Wrapper Integration

Implemented for Sprint 10B:

- `backend/scripts/hermes_agent_server.py` exposes `POST /agent`;
- the wrapper loads the current domain, intake, lifecycle, contract,
  escalation, and safety skills;
- `HERMES_AGENT_MODE=local` provides a deterministic local adapter because no
  standalone Hermes runtime is present in the repository yet;
- free-text or fenced JSON output can be parsed, but only valid
  `AgentResponse` is returned;
- invalid output causes HTTP `502`, which makes `HermesRealClient` and
  `HermesService` use the existing safe fallback;
- the wrapper has no persistence or Telegram delivery permissions.

The full integration note is in `backend/docs/HERMES_AGENT_INTEGRATION.md`.

### LLM Agent Mode

Implemented for Sprint 18:

- `HERMES_AGENT_MODE=fake|local|llm` selects the wrapper runtime;
- `LLM_PROVIDER=openai` is supported through the wrapper only;
- OpenAI credentials and model selection are read from environment variables and
  are not exposed through logs or `/config/status`;
- the wrapper builds the prompt from the system prompt, selected skills,
  `IncomingMessage`, conversation history, business context, response contract,
  and safety rules;
- the wrapper requests strict JSON compatible with `AgentResponse`;
- model output is parsed and validated with Pydantic before it reaches
  `HermesRealClient`;
- invalid model output, timeout, or provider HTTP error returns controlled
  failure so `HermesService` uses safe fallback;
- DecisionRecords and HumanReview continue to work because execution still goes
  through `ConversationService`.

Required production discipline:

- keep production V1 in `HERMES_MODE=mock` until real-mode evals are reviewed;
- run `make evals-agent-llm` before any staging/prod activation;
- test with `/messages/test` or an isolated backend before Telegram traffic;
- review DecisionRecords for traceability and action quality;
- keep fallback and HumanReview active for all real-agent tests.

The full LLM mode note is in `backend/docs/HERMES_LLM_AGENT.md`.

### Decision Records

Implemented:

- `DecisionRecord` and `DecisionRecordCreate` schemas;
- `DecisionAuditService`;
- `decision_records` persistence collection;
- `GET /audit/decisions`;
- `GET /audit/decisions/{decision_id}`;
- ConversationService integration for real and test message processing.

Problem it solves:

- creates an audit trail for every Hermes decision handled by the backend;
- connects messages, conversations, incidents, and agent decisions with
  `trace_id`;
- makes fallback usage visible without exposing secrets;
- records version placeholders for prompt, skill, and response contract.

What is recorded now:

- `trace_id`;
- `conversation_id`;
- optional `message_id`;
- optional `incident_id`;
- `channel`;
- `hermes_mode`;
- `action_type`;
- `incident_should_create`;
- `pest_type`;
- `priority`;
- `fallback_used`;
- `fallback_reason`;
- `prompt_version`;
- `skill_version`;
- `response_contract_version`;
- `created_at`;
- safe metadata such as message type and missing fields.

How to inspect records:

```bash
curl http://127.0.0.1:8000/audit/decisions
curl "http://127.0.0.1:8000/audit/decisions?conversation_id=telegram:user-1"
curl "http://127.0.0.1:8000/audit/decisions?fallback_used=true"
curl http://127.0.0.1:8000/audit/decisions/<decision_id>
```

Current limitations:

- audit records are append-only by convention, not yet enforced by permissions;
- no panel screen exists yet for audit review;
- prompt and skill versions are static placeholders;
- Firebase Auth can identify an operator at the request boundary, but operator
  activity is not yet written into domain audit records.

## Current Harness Boundaries

Hermes may propose:

- reply text;
- action type;
- missing fields;
- incident proposal.

Backend owns:

- message normalization;
- persistence;
- incident creation;
- allowed incident updates;
- fallback creation;
- Telegram delivery;
- manual technician and visit APIs;
- configuration and diagnostics.

Hermes does not own:

- technician assignment;
- agenda writes;
- route optimization;
- calendar synchronization;
- operational document creation.

Humans currently own:

- reviewing incidents in the panel;
- reviewing escalated and fallback cases in the human review queue;
- creating technicians and visits manually;
- assigning visits to technicians;
- changing basic operational status;
- adding internal notes;
- generating and reviewing internal operational documents.

### Operational Documents

Operational documents are deterministic backend templates over persisted
incident and visit data. They are not Hermes-authored artifacts and are not
official legal certificates. Future agent-proposed document content should enter
through a reviewable backend service boundary rather than direct agent writes.

## Pending Harness Capabilities

### Evaluation Cases

Create a repeatable evaluation suite with representative pest-control
conversations:

- complete cockroach case;
- incomplete location;
- incomplete affected area;
- ambiguous pest type;
- photo-only message;
- urgent or vulnerable-person case;
- abusive or irrelevant message;
- repeated follow-up in the same conversation.

Each case should define expected action type, missing fields, incident proposal,
priority, and reply quality criteria.

### Conversation Traceability

Add trace ids that connect:

- inbound message;
- conversation id;
- Hermes request;
- Hermes response;
- created incident;
- outbound message;
- operator updates.

This should be visible in logs and persisted metadata.

### Decision Audit

Persist decision records for agent outputs:

- agent mode;
- prompt version;
- response contract version;
- proposed action;
- validation result;
- fallback reason if used.

This gives later explainability without storing unnecessary secrets.

### Prompt and Skill Versioning

Version:

- system prompt;
- business context;
- response schema;
- extraction heuristics;
- tool definitions when introduced.

Every decision should be attributable to the versions active at the time.

### Human Review Queue

Implemented:

- `HumanReviewItem` and controlled update schema;
- `HumanReviewService`;
- `human_review_items` persistence collection;
- `GET /human-review`;
- `GET /human-review/{item_id}`;
- `PATCH /human-review/{item_id}`;
- panel routes `/human-review` and `/human-review/:id`.

Items are created automatically for:

- fallback incidents;
- agent escalation;
- urgent cases;
- sensitive cases marked in response metadata.

Current limitations:

- no user identity beyond optional `assigned_to`;
- no SLA or reminder logic;
- no audit history of status changes yet;
- no dedicated metrics dashboard for review backlog.

### Tool Permissions

Before Hermes can use tools, define:

- allowed tools;
- read/write permissions;
- approval requirements;
- timeout and retry policy;
- audit log for every tool call.

### Quality Metrics

Track operational and agent-quality metrics:

- create_incident precision;
- missing-field recall;
- fallback rate;
- invalid response rate;
- time to human review;
- incident status progression;
- user correction rate.

### Conversation Replay

Support replaying stored conversations against:

- current mock client;
- candidate real Hermes endpoint;
- new prompt versions;
- new schema versions.

Replay should never send Telegram messages by default.

### Pest-Control Test Dataset

Build a curated dataset of Spanish pest-control conversations:

- Telegram-style short messages;
- noisy user input;
- location variants;
- pest synonyms;
- urgency indicators;
- follow-up messages;
- attachment metadata cases.

Use it for regression tests and prompt evaluation.

## Roadmap of Harness Maturity

### Stage 1: Contract Harness

Status: mostly implemented.

- normalized messages;
- AgentResponse contract;
- Pydantic validation;
- mock agent;
- safe fallback;
- backend tests.

### Stage 2: Operational Harness

Status: partially implemented.

- real Telegram;
- optional WhatsApp sandbox/Meta adapter;
- persisted conversations/messages/incidents;
- config status;
- operational panel;
- API-key or Firebase Auth protection for operational endpoints;
- incident status updates;
- local scripts and smoke tests.

Remaining:

- review queue semantics;
- richer audit records;
- operator activity tracking.

### Stage 3: Evaluation Harness

Status: partially implemented.

- conversation test dataset;
- expected-output cases;
- replay runner;
- quality metrics;
- prompt/schema version comparisons.
- optional Hermes LLM shadow mode for live comparison without side effects.

## Shadow Mode

Hermes Shadow Mode lets the system compare the active Hermes decision against a
secondary Hermes endpoint, usually the LLM wrapper, without changing customer
behavior.

When `HERMES_SHADOW_MODE=false`, nothing changes.

When enabled:

- `ConversationService` still uses the primary `HermesService` response for the
  customer reply and business actions.
- The shadow Hermes endpoint is called after the primary decision.
- The shadow response is never sent to Telegram, WhatsApp, or any user-facing
  channel.
- The shadow response never creates incidents, visits, documents, or calendar
  events.
- A `ShadowDecisionRecord` is written to `shadow_decision_records` for
  comparison.

Stored comparison fields include:

- trace ID;
- conversation ID;
- channel;
- primary/shadow action type;
- primary/shadow priority;
- primary/shadow pest type;
- primary/shadow `should_create`;
- differences;
- shadow fallback/error state.

The backend sends `X-Hermes-Trace-Id` to the shadow endpoint so backend logs,
wrapper logs, OpenAI calls, `DecisionRecord`, and `ShadowDecisionRecord` can be
correlated without logging prompts or secrets.

Shadow failures are normalized for audit, for example:

```text
HermesClientError:timeout
HermesClientError:connection_error
HermesClientError:http_401
HermesClientError:invalid_contract
UnexpectedError:<ExceptionClass>
```

Shadow records can be queried through protected endpoints:

```text
GET /audit/shadow-decisions
GET /audit/shadow-decisions/{id}
```

The operations panel also includes an `Evaluación IA` section:

```text
/audit/shadow-decisions
/audit/shadow-decisions/:id
```

This UI is read-only and uses the same admin authentication as the rest of the
panel. It is for comparing primary vs shadow decisions, not for approving agent
actions.

Operator interpretation:

- `Sistema actual` is the decision that actually affected the user flow.
- `IA en sombra` is the simulated LLM decision.
- `Coinciden` means the core decision fields match.
- `Hay diferencias` means a human should review whether the IA criterion is
  better or worse.
- `Error de IA en sombra` means shadow evaluation failed while the primary flow
  remained safe.

### Stage 4: Tool Harness

Status: experimental PoC.

- `ToolRequest`, `ToolDecision`, and `ToolExecutionRecord` schemas exist.
- `HermesToolHarness` gates experimental Nous Hermes tool proposals.
- `NousHermesRuntimeAdapter` converts PoC output into `AgentResponse` or
  `ToolRequest`.
- The local runner executes three controlled scenarios without external
  effects:
  - visit scheduling proposal;
  - Gmail draft proposal;
  - dangerous WhatsApp chemical-advice request.
- All PoC `ToolExecutionRecord` entries must remain `executed=false` and
  `external_effect=false`.
- Gmail send, direct Firestore writes, and dangerous chemical channel messages
  are blocked.
- Calendar and channel drafts require human approval.

Run the local controlled PoC from the backend folder:

```bash
python experiments/nous_hermes_controlled/run_controlled_poc.py
```

Reports are written to ignored local files under `backend/evals/results/`.

Remaining:

- real Nous Hermes process invocation;
- persisted tool audit collection;
- approval queue integration;
- operator UI for ToolRequests;
- production rollout controls.

Sprint 24 adds the first operator review surface for tool proposals:

```text
GET /tools/executions
GET /tools/executions/{id}
PATCH /tools/executions/{id}
```

The panel exposes these records under:

```text
/tools/executions
/tools/executions/:id
```

Visible label: `Acciones IA`.

This is still review-only. Operators can mark a proposal as `approved`,
`rejected`, `needs_more_info`, or `dismissed`, add notes, and optionally store an
approved payload for a future controlled-execution phase. Approval does not
execute Gmail, Calendar, Telegram, WhatsApp, or Firestore tools. Tool records
must remain `executed=false` and `external_effect=false`.

### Stage 4.1: Gmail Draft Execution

Status: controlled and disabled by default.

Sprint 25 introduces the first low-risk real tool execution:

```text
POST /tools/executions/{id}/execute
```

Only `gmail.create_draft` is executable. Preconditions:

- `review_status=approved`;
- `executed=false`;
- `GMAIL_TOOLS_ENABLED=true`;
- `GMAIL_DRAFT_EXECUTION_ENABLED=true`;
- valid Gmail credentials are configured;
- payload contains `recipient`, `subject`, and `body`.

The endpoint creates a Gmail draft and stores a safe `execution_result` with
provider and draft/message ids. It does not send email. `gmail.send_email`,
Calendar, Telegram, WhatsApp, and direct Firestore tools remain blocked.

Operational validation:

- `make gmail-draft-check` verifies Gmail auth without creating drafts.
- `CONFIRM_CREATE_GMAIL_DRAFT=true make gmail-draft-check` creates a controlled
  test draft only.
- `SEED_APPROVED_GMAIL_DRAFT=true make seed-tool-executions` prepares an
  approved `gmail.create_draft` action for panel QA.

Rollback is flag-based: set `GMAIL_DRAFT_EXECUTION_ENABLED=false` and
`GMAIL_TOOLS_ENABLED=false`.

### Stage 4.2: Hermes Agent Pilot Mode

Status: implemented, disabled by default.

Sprint 26 adds a controlled Pilot Mode in front of Hermes Agent. The active
orchestrator is still `ConversationService`; Telegram and WhatsApp adapters are
unchanged; the LLM still cannot write to Firestore or call tools directly.

Pilot routing is:

```text
IncomingMessage
-> ConversationService
-> Pilot Gate
-> Hermes Agent only if eligible
-> AgentResponse validation
-> DecisionRecord/HumanReview/fallback
```

Configuration:

```text
HERMES_PILOT_MODE=false
HERMES_PILOT_SAMPLE_RATE=1.0
HERMES_PILOT_ALLOWED_CHANNELS=telegram
HERMES_PILOT_REQUIRE_GATE=true
HERMES_PILOT_MAX_RESPONSE_LENGTH=800
```

Eligible low-risk messages can use Hermes Agent as the primary reply. Sensitive
messages are routed to Human Review, and incomplete or pricing-related messages
fall back to the current mock behavior. Any agent error, fallback response, or
oversized reply falls back to the primary mock flow and is audited in
`DecisionRecord.metadata` with `pilot_used`, `pilot_blocked`,
`pilot_policy_rule`, and `pilot_risk_flags`.

Production rollback remains a single flag:

```text
HERMES_PILOT_MODE=false
```

### Runtime Provider Boundary

Status: implemented.

The agent runtime is encapsulated behind neutral provider contracts under:

```text
backend/app/harness/
backend/app/harness/runtime.py
backend/app/harness/contracts.py
backend/app/harness/providers/llm_provider.py
backend/app/harness/providers/mock_provider.py
backend/app/harness/providers/hermes_http_provider.py
```

`HermesService` remains the stable service facade used by
`ConversationService`, evals, shadow mode, and pilot mode. Internally it now
routes:

```text
AGENT_PROVIDER=llm         -> LLMRuntimeProvider, primary path
AGENT_PROVIDER=mock        -> MockAgentRuntimeProvider
AGENT_PROVIDER=nous_hermes -> HermesHttpRuntimeProvider, experimental
```

Legacy compatibility remains while deployments migrate:

```text
HERMES_MODE=mock -> mock provider when AGENT_PROVIDER is unset
HERMES_MODE=real -> nous_hermes provider when AGENT_PROVIDER is unset
```

This keeps Hermes Agent, Nous-style runtimes, HTTP wrappers, skills, and future
providers out of the orchestrator. Providers must return `AgentResponse`; tool
use remains mediated separately through `ToolRequest`, `ToolDecision`, audit,
and backend services.

Hermes Pest Harness is the core product architecture. `LLMRuntimeProvider` is
the primary inference adapter; Nous/Hermes Agent remains an experimental
provider until comparative evals, shadow stability, pilot approval, and rollback
criteria justify a broader role.

### Product Skill Registry

Status: implemented.

Product skills live under:

```text
backend/app/skills/
backend/app/skills/contracts.py
backend/app/skills/registry.py
backend/app/skills/definitions/
```

These skills are owned by Hermes Pest Harness, not by Nous/Hermes Agent. The
initial registry contains:

- `classify_pest`;
- `request_missing_info`;
- `create_incident`;
- `escalate_to_human`;
- `suggest_visit`;
- `summarize_case`.

`HermesService` attaches the registry output to `AgentRuntimeRequest` so any
runtime provider can use the same product capabilities. Skills are declarative:
they describe allowed outputs, forbidden effects, risk level, and instructions.
They do not write to Firestore, create incidents, schedule visits, send channel
messages, or execute tools. Backend services remain responsible for all real
effects.

The older markdown skills under `hermes/skills` are retained for experimental
HTTP-wrapper compatibility only. They should be treated as adapter material,
not as the long-term source of product capability definitions.

### Tool Registry

Status: implemented.

Backend tools live under:

```text
backend/app/tools/
backend/app/tools/contracts.py
backend/app/tools/registry.py
backend/app/tools/definitions/
```

The first tool registry separates execution mechanics from product skills:

- `create_incident_tool`;
- `get_incident_tool`;
- `list_incidents_tool`;
- `escalate_to_human_tool`;
- `suggest_visit_tool`.

Providers receive safe tool metadata through `AgentRuntimeRequest`, but they are
not allowed to execute tools. Skills also cannot execute tools or write to
Firestore. A provider may propose intent; the backend converts that proposal
into reviewed decisions and service calls.

The operating model is:

```text
Skill    = what Hermes Pest knows how to reason about
Policy  = whether a proposed tool/action may proceed
Tool     = technical backend action under policy
Provider = model/runtime that proposes
Service  = backend owner that changes real state
```

Firestore remains the source of truth. Tool execution must pass through backend
services and the existing review/audit controls.

### Tool Execution Lifecycle

Status: implemented as an internal contract.

Execution contracts live under:

```text
backend/app/tools/execution_contracts.py
```

Every tool execution should be representable as:

```text
ToolExecutionRequest -> ToolExecutionResult | ToolExecutionError
```

The formal lifecycle states are:

```text
PENDING -> APPROVED -> EXECUTED
PENDING -> DENIED
PENDING -> REQUIRES_HUMAN_REVIEW
PENDING -> APPROVED -> FAILED
```

`ToolExecutionService` owns the lifecycle. Providers do not construct execution
results, policies do not execute, and skills do not decide authorization.

Each execution contract answers:

- which tool was requested;
- who or what provider proposed it;
- what payload was proposed;
- what status the execution reached;
- what result or error was produced.

The public `ToolExecutionRecord` API remains compatible with the existing panel,
while the internal request/result/error contracts prepare the harness for Gmail,
Calendar, CRM, WhatsApp, agenda, presupuesto, and future audit records.

### Harness Audit Log

Status: implemented as an in-memory harness layer.

Audit modules live under:

```text
backend/app/audit/
backend/app/audit/contracts.py
backend/app/audit/in_memory_repository.py
backend/app/audit/service.py
```

The audit log records important Agent Harness events:

```text
Provider -> Skill -> Tool -> PolicyEngine -> ToolExecutionService -> Resultado
```

Initial event types:

- `PROVIDER_SELECTED`;
- `TOOL_PROPOSED`;
- `POLICY_EVALUATED`;
- `TOOL_EXECUTION_STARTED`;
- `TOOL_EXECUTION_COMPLETED`;
- `TOOL_EXECUTION_FAILED`;
- `HUMAN_REVIEW_REQUIRED`.

Current storage is in memory only. It prepares structured traceability before a
future persistent audit repository. It does not write to Firestore yet.

Responsibility split:

```text
Provider = razona
Skill = define capacidad
PolicyEngine = autoriza
ToolExecutionService = ejecuta
AuditService = registra
```

`AuditService` is best-effort. If audit recording fails, it returns safely and
does not block the main execution path. The audit layer never decides policies
and never executes tools.

### Policy Engine

Status: implemented.

Policy modules live under:

```text
backend/app/policies/
backend/app/policies/contracts.py
backend/app/policies/default_rules.py
backend/app/policies/engine.py
```

The `PolicyEngine` receives a `PolicyContext` and returns one of:

```text
ALLOW
DENY
REQUIRE_HUMAN_REVIEW
```

Initial rules:

- `create_incident_tool`: `ALLOW`;
- `get_incident_tool`: `ALLOW`;
- `list_incidents_tool`: `ALLOW`;
- `escalate_to_human_tool`: `ALLOW`;
- `suggest_visit_tool`: `REQUIRE_HUMAN_REVIEW`;
- unknown tools: `DENY`.

The Policy Engine does not execute tools, modify Firestore, or depend on a
provider. It is consulted before controlled tool execution. Providers and skills
cannot bypass it; backend services only run after the harness has authorized the
action or routed it to human review.

#### Policy Enforcement Boundary

The controlled execution boundary is:

```text
Route /tools/executions/{id}/execute
-> PolicyEngine
-> ToolExecutionService
-> controlled backend executor/service
```

Only the protected route may call `ToolExecutionService.execute_execution_record`
in application code. The route first builds a `PolicyContext`, asks
`PolicyEngine` for the final decision, and only delegates execution when the
decision is `ALLOW`.

`DENY` returns a safe blocked response. `REQUIRE_HUMAN_REVIEW` keeps the record
reviewable by a human operator and does not execute the external action.

Providers, skills, and registries are intentionally non-execution layers:

- providers reason and propose structured responses or actions;
- skills describe what Hermes Pest knows how to do;
- registries expose metadata;
- tools describe backend actions under policy;
- services perform real state changes only after harness authorization.

### Stage 5: Production Governance

Status: pending.

- authentication and authorization;
- tenant/company boundaries if SaaS arrives;
- data retention policy;
- incident audit history;
- monitoring dashboards;
- alerting on fallback or invalid-response spikes.

## Sprint 6.5 Review Summary

The current system is ready to continue toward a fuller agent harness. The most
important next step is not adding new channels, but improving evaluation,
traceability, and auditability around Hermes decisions.
