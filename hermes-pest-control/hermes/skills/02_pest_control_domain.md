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
- `chinche`, `chinches`, `chinches de cama` -> `chinches`
- `avispa`, `avispas`, `nido de avispas` -> `avispas`
- if the pest is unclear, set `pest_type` to `null` and collect `pest_type`.

Extract fields atomically:

- `location` means locality/town/city only, for example `Torremolinos`,
  `Málaga`, `Marbella`, `Fuengirola`, `Benalmádena`.
- Do not put room, business context, or extra sentence fragments in `location`.
  Example: from `cocina de un restaurante en Málaga`, use
  `affected_area="cocina"` and `location="Málaga"`, not
  `location="restaurante en Málaga"`.
- `affected_area` means the zone/room/site where the issue appears, for example
  `cocina`, `garaje`, `baño`, `jardín`, `almacén`, `dormitorio`,
  `habitación`, `terraza`.
- Normalize `habitación` to `dormitorio` when the context is bedbugs/chinches.

Priority rules:

- Use `urgent` for possible intoxication, chemical exposure, pets exposed to
  products, children/vulnerable people at risk, or food-business critical risk.
- Use `urgent` when a pet is exposed to a product or is directly at risk from
  unsafe chemical/product handling.
- Use `urgent` for restaurants, bars, food businesses, or kitchens in food
  businesses with active pests.
- Use `urgent` for wasp nests or repeated wasp activity near living areas when
  children, vulnerable people, or immediate safety concern are mentioned.
- Use `urgent` for chinches or other interior pests when babies, small children,
  elderly people, pregnant people, respiratory-risk people, or other vulnerable
  people are mentioned.
- Use `high` for `cucarachas`, `roedores`, `chinches`, angry customers,
  product/chemical requests, guarantee requests, and fixed-price demands that
  need human review.
- Use `high` for roedores reported indoors when no immediate health emergency is
  described.
- Plain `chinches` in `dormitorio` with pest, area, and locality present is a
  high-priority incident, not urgent and not automatic escalation, unless the
  user also reports bites, vulnerable people, strong health concern, or high
  affectation.
- Use `high` for wasps/avispas near the home when there is no vulnerable-person
  or immediate safety signal.
- Product/chemical questions without reported exposure symptoms are `high`,
  not `urgent`. Escalate them, but reserve `urgent` for actual exposure,
  intoxication symptoms, pets, vulnerable people, or food-business critical
  risk.
- Use `medium` for lower-risk ordinary cases such as ants when no vulnerable
  people, food business, chemical exposure, or urgency is mentioned.
- Use `low` only when the user clearly describes a minor, non-urgent issue.

Typo tolerance:

- Correct obvious Spanish misspellings when the intended pest, area, and
  locality are high-confidence, for example `cucaraxa` -> `cucarachas`,
  `cosina` -> `cocina`, `ormigas` -> `hormigas`, `jardin` -> `jardín`,
  `malaga` -> `Málaga`.
- If the typo makes a required field uncertain, preserve the fields that are
  clear and use `collect_missing_data` for the uncertain fields.
