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
- placeholder adapters for WhatsApp, webchat, and email

Role in the harness:

- normalize external channel payloads;
- hide transport-specific details;
- send responses without business decisions.

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

Next steps:

- add multi-turn conversation cases;
- add prompt and schema version metadata;
- add replay from stored conversations;
- add quality metrics over repeated runs;
- add a curated Spanish pest-control dataset;
- separate smoke cases from safety/regression gates if the suite grows.

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
- no operator identity is recorded because login does not exist yet.

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
- configuration and diagnostics.

Humans currently own:

- reviewing incidents in the panel;
- changing basic operational status;
- adding internal notes.

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

Formalize a queue for:

- fallback incidents;
- low-confidence cases;
- urgent cases;
- cases missing required fields;
- operator overrides.

The current panel is the first step, but it is not yet a full queue.

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
- persisted conversations/messages/incidents;
- config status;
- operational panel;
- incident status updates;
- local scripts and smoke tests.

Remaining:

- review queue semantics;
- richer audit records;
- operator activity tracking.

### Stage 3: Evaluation Harness

Status: pending.

- conversation test dataset;
- expected-output cases;
- replay runner;
- quality metrics;
- prompt/schema version comparisons.

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
