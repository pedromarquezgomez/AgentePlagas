# Hermes Evaluations

Offline evaluation harness for Hermes Pest Control.

The runner loads JSON cases from `backend/evals/cases`, builds
`IncomingMessage` objects, calls `HermesService` in mock mode by default, and
checks the returned `AgentResponse` against expected decisions and reply text
rules.

It does not call Telegram, does not send channel messages, and does not persist
evaluation traces to Firestore.

## Run

From `backend`:

```bash
python -m evals.run_evals
```

From the repository root:

```bash
make evals
```

Optional JSON export:

```bash
cd backend
python -m evals.run_evals --output evals/results/latest.json
```

## Case Format

```json
{
  "id": "cockroach_kitchen_complete",
  "description": "Cliente informa cucarachas con datos suficientes",
  "input": {
    "channel": "telegram",
    "external_user_id": "eval-user-1",
    "external_chat_id": "eval-chat-1",
    "message_type": "text",
    "text": "Tengo cucarachas en la cocina en Torremolinos desde hace una semana",
    "attachments": [],
    "metadata": {}
  },
  "expected": {
    "action_type": "create_incident",
    "pest_type": "cucarachas",
    "location": "Torremolinos",
    "affected_area": "cocina",
    "priority": "high",
    "should_create": true
  },
  "must_include_in_reply": [
    "registrado",
    "equipo"
  ],
  "must_not_include_in_reply": [
    "garantizado",
    "producto químico",
    "precio cerrado"
  ]
}
```

Only fields present in `expected` are asserted. Supported expected fields are:

- `action_type`
- `missing_fields`
- `should_create`
- `pest_type`
- `location`
- `affected_area`
- `priority`

## Trace Fields

Each result includes:

- `eval_run_id`
- `case_id`
- `trace_id`
- `hermes_mode`
- `action_type`
- `incident_should_create`
- `pest_type`
- `priority`
- `fallback_used`
- `fallback_reason`
- `response_contract_version`
- `passed`
- `failure_reasons`
