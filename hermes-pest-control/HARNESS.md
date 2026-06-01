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

Shadow records can be queried through protected endpoints:

```text
GET /audit/shadow-decisions
GET /audit/shadow-decisions/{id}
```

The operations panel also includes an `Evaluación LLM` section:

```text
/audit/shadow-decisions
/audit/shadow-decisions/:id
```

This UI is read-only and uses the same admin authentication as the rest of the
panel. It is for comparing primary vs shadow decisions, not for approving agent
actions.

### Stage 4: Tool Harness

Status: pending.

- tool registry;
- tool permissions;
- approval gates;
- tool-call audit;
- dry-run mode;
- sandboxed tool tests.

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
