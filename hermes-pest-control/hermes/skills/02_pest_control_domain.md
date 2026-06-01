# 02 Pest Control Domain

The domain model starts with these business concepts:

- Client: person or business requesting service.
- Conversation: communication thread with a client through one channel.
- Incident: operational pest control case.
- Escalation: handoff to a human operator.

Useful incident data:

- Pest type.
- Location.
- Affected area.
- Priority.
- Status.
- Summary.
- Photos or other attachments.

Priority should consider pest severity, health risk, vulnerable people, business impact, and recurrence.

## Deterministic Pest And Priority Rules

Normalize common Spanish pest terms:

- `cucaracha`, `cucarachas` -> `cucarachas`
- `rata`, `ratas`, `ratón`, `raton`, `ratones`, `roedor`, `roedores` -> `roedores`
- `hormiga`, `hormigas` -> `hormigas`
- if the pest is unclear, set `pest_type` to `null` and collect `pest_type`.

Extract fields atomically:

- `location` means locality/town/city only, for example `Torremolinos`,
  `Málaga`, `Marbella`, `Fuengirola`, `Benalmádena`.
- Do not put room, business context, or extra sentence fragments in `location`.
  Example: from `cocina de un restaurante en Málaga`, use
  `affected_area="cocina"` and `location="Málaga"`, not
  `location="restaurante en Málaga"`.
- `affected_area` means the zone/room/site where the issue appears, for example
  `cocina`, `garaje`, `baño`, `jardín`, `almacén`.

Priority rules:

- Use `urgent` for possible intoxication, chemical exposure, pets exposed to
  products, children/vulnerable people at risk, or food-business critical risk.
- Use `urgent` for restaurants, bars, food businesses, or kitchens in food
  businesses with active pests.
- Use `high` for `cucarachas`, `roedores`, `chinches`, angry customers,
  product/chemical requests, guarantee requests, and fixed-price demands that
  need human review.
- Product/chemical questions without reported exposure symptoms are `high`,
  not `urgent`. Escalate them, but reserve `urgent` for actual exposure,
  intoxication symptoms, pets, vulnerable people, or food-business critical
  risk.
- Use `medium` for lower-risk ordinary cases such as ants when no vulnerable
  people, food business, chemical exposure, or urgency is mentioned.
- Use `low` only when the user clearly describes a minor, non-urgent issue.
