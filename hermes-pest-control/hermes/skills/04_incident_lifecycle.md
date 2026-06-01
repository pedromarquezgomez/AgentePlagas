# 04 Incident Lifecycle

Initial incident status:

- `pending_review`: created from intake and pending human or operational review.

Future statuses:

- `triaged`
- `scheduled`
- `assigned`
- `in_progress`
- `resolved`
- `cancelled`

Incident creation should be handled by `IncidentService`, not by channel adapters or Hermes directly.

Hermes may recommend an action, but backend services own persistence and lifecycle transitions.

## Incident Creation Semantics

When `action.type` is `create_incident`:

- `incident.should_create` must be `true`;
- include `pest_type`, `location`, `affected_area`, `priority`, and `summary`;
- do not set `status` unless explicitly required by the response contract;
- the backend will create the incident with `pending_review`.

When `action.type` is `collect_missing_data`:

- normally set `incident.should_create` to `false`;
- do not say the incident was registered;
- ask only for the missing required fields.

When `action.type` is `escalate_to_human`:

- set `incident.should_create` to `true` when the message gives enough
  operational context or the risk itself should be recorded;
- include any fields that can be extracted safely;
- use priority `urgent` for safety/health/food-business critical risk;
- use priority `high` for complaints, guarantees, fixed-price pressure, and
  non-immediate but sensitive review cases.

Escalation is not a reason to drop extracted fields. If a message says
`cucarachas en la cocina en Torremolinos`, preserve:

- `pest_type="cucarachas"`
- `affected_area="cocina"`
- `location="Torremolinos"`
