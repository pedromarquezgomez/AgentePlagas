# 03 Conversation Intake

Conversation intake converts a normalized message into an operational decision.

Current sprint behavior:

1. Receive `IncomingMessage`.
2. Build `conversation_id` as `channel:external_user_id`.
3. Send message to `HermesService`.
4. If Hermes returns `create_incident`, call `IncidentService`.
5. Return `AgentResponse`.

Future behavior:

- Load existing conversation state from Firestore.
- Store message history.
- Track missing fields.
- Resume intake across multiple messages.

## Action Selection Rules

Use the minimum safe action. Do not ask for extra information when the current
message already has enough data for the action.

Required fields for a normal incident:

- `pest_type`
- `affected_area`
- `location`

Use `create_incident` when all three required fields are present and there is no
mandatory escalation trigger.

Use `collect_missing_data` only when one or more required fields are missing and
there is no mandatory escalation trigger.

Use `escalate_to_human` when a mandatory escalation trigger is present, even if
some fields are missing.

Do not require these fields before creating an initial incident:

- full street address;
- phone number;
- photos;
- preferred appointment time;
- exact number of pests;
- customer name.

These details can be requested later by the human team or operations panel.

## Missing Field Rules

If collecting missing data, populate `action.missing_fields` exactly with the
missing required fields:

- missing pest type -> `["pest_type"]`
- missing affected zone/room -> `["affected_area"]`
- missing locality/town -> `["location"]`

Do not include fields that are already present.

The reply must name the missing concept in Spanish:

- missing `location`: include `localidad`;
- missing `affected_area`: include `zona`;
- missing `pest_type`: include `plaga`;

## Examples

Input: `Tengo cucarachas en la cocina en Torremolinos desde hace una semana`

- `pest_type`: `cucarachas`
- `affected_area`: `cocina`
- `location`: `Torremolinos`
- action: `create_incident`
- priority: `high`

Input: `Tengo cucarachas en la cocina desde hace una semana`

- missing only `location`
- action: `collect_missing_data`
- `missing_fields`: `["location"]`
- reply includes `localidad`

Input: `Tengo hormigas en Málaga desde el fin de semana`

- missing only `affected_area`
- action: `collect_missing_data`
- `missing_fields`: `["affected_area"]`
- reply includes `zona`

Input: `Tengo un problema en la cocina en Fuengirola`

- missing only `pest_type`
- action: `collect_missing_data`
- `missing_fields`: `["pest_type"]`
- reply includes `plaga`
