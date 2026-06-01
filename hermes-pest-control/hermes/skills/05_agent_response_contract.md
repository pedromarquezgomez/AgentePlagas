# 05 Agent Response Contract

`AgentResponse` is the contract returned by Hermes-facing logic.

Fields:

- `reply`: text to send back to the user.
- `action`: machine-readable backend instruction.
- `incident`: incident proposal or context.

Known action types:

- `create_incident`
- `collect_missing_data`
- `escalate_to_human`

Hermes responses should be deterministic enough for backend services to execute safely.

## Strict Output Rules

Return only JSON compatible with `AgentResponse`.

Do not return markdown.

Do not return explanatory text outside the JSON.

Do not invent unsupported `action.type` values.

Conceptual product discussions may mention `reply_only`, but
`AgentResponse.v1` does **not** support `reply_only` yet. Until the backend
schema is upgraded, never output `reply_only`.

Valid `action.type` values in this codebase are exactly:

- `create_incident`
- `collect_missing_data`
- `escalate_to_human`

`incident.priority` must be one of:

- `low`
- `medium`
- `high`
- `urgent`

## Required Reply Wording

For `create_incident`, the reply must include:

- `registrado`
- `equipo`

For `collect_missing_data`, the reply must include the missing concept:

- missing location -> include `localidad`
- missing affected area -> include `zona`
- missing pest type -> include `plaga`

For `escalate_to_human`, the reply must include:

- `equipo`
- `revise`

For safety-related escalation, the reply must also include:

- `seguridad`

Never include:

- `garantizado`
- `precio cerrado`
- `producto químico`

Use safer wording such as `producto` or `tratamiento` only when needed, and do
not recommend specific chemicals.

## Few-Shot Contract Examples

Complete ordinary case:

```json
{
  "reply": "Gracias por la información. He registrado el aviso para que el equipo lo revise.",
  "action": {"type": "create_incident", "missing_fields": []},
  "incident": {
    "should_create": true,
    "pest_type": "cucarachas",
    "location": "Torremolinos",
    "affected_area": "cocina",
    "priority": "high",
    "summary": "Cliente informa de presencia de cucarachas en cocina en Torremolinos.",
    "id": null,
    "conversation_id": null,
    "status": null
  },
  "metadata": {}
}
```

Missing locality:

```json
{
  "reply": "Para registrar el aviso necesito saber la localidad donde ocurre.",
  "action": {"type": "collect_missing_data", "missing_fields": ["location"]},
  "incident": {
    "should_create": false,
    "pest_type": "cucarachas",
    "location": null,
    "affected_area": "cocina",
    "priority": "medium",
    "summary": null,
    "id": null,
    "conversation_id": null,
    "status": null
  },
  "metadata": {}
}
```

Pet or possible exposure:

```json
{
  "reply": "Por seguridad, he dejado el caso para que el equipo lo revise antes de darte indicaciones.",
  "action": {"type": "escalate_to_human", "missing_fields": []},
  "incident": {
    "should_create": true,
    "pest_type": "roedores",
    "location": "Málaga",
    "affected_area": "garaje",
    "priority": "urgent",
    "summary": "Mascota expuesta a un producto relacionado con roedores. Requiere revisión humana.",
    "id": null,
    "conversation_id": null,
    "status": null
  },
  "metadata": {}
}
```

Price request without enough data:

```json
{
  "reply": "El equipo revise el caso antes de dar condiciones concretas. Necesitamos más datos operativos para valorar el aviso.",
  "action": {"type": "escalate_to_human", "missing_fields": []},
  "incident": {
    "should_create": true,
    "pest_type": null,
    "location": null,
    "affected_area": null,
    "priority": "high",
    "summary": "Cliente solicita condiciones cerradas sin datos suficientes. Requiere revisión humana.",
    "id": null,
    "conversation_id": null,
    "status": null
  },
  "metadata": {}
}
```
