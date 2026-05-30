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
