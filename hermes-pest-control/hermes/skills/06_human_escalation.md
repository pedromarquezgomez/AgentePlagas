# 06 Human Escalation

Escalate to a human when:

- There is an immediate health or safety risk.
- The client reports chemical exposure.
- The user is angry, confused, or asks for a person.
- The incident is outside supported pest control workflows.
- Legal, medical, or compliance advice might be required.

`EscalationService` will later own escalation policies, assignment, and notification routing.

## Mandatory Escalation Triggers

Use `action.type="escalate_to_human"` for any of these:

- possible intoxication;
- chemical exposure;
- user says they have inhaled, touched, mixed, or used a product and feels
  unwell;
- pet exposure, for example dog/cat touched a product;
- children, elderly people, pregnant people, or vulnerable people at risk;
- restaurant, bar, food business, kitchen in a food business, or critical food
  handling context;
- user asks what chemical product to use;
- user asks whether to mix products, bleach, ammonia, or similar substances;
- user demands a total guarantee;
- user demands a fixed/closed price without enough operational data;
- user is very angry, threatens complaint, or explicitly asks for review by a
  person.

Escalation does not mean `incident.should_create=false`. For most escalation
cases, create an incident so the team can review it.

Use `priority="urgent"` for:

- possible intoxication;
- pet or vulnerable-person exposure;
- food-business critical risk;
- restaurant/bar/kitchen business with active pest report.

Use `priority="high"` for:

- angry customer or complaint;
- chemical/product request without exposure symptoms;
- product-mixing request;
- guarantee or fixed-price pressure;
- roedores or cucarachas when no immediate health emergency is described.

Do not mark a chemical/product question as `urgent` just because the user asks
what to use. It becomes `urgent` only when the user reports exposure,
intoxication symptoms, pets, vulnerable people, or food-business critical risk.

## Escalation Reply Rules

The reply must not give technical pesticide instructions.

The reply must include:

- `equipo`
- `revise`

For health, safety, product, pet, vulnerable-person, or food-business cases,
also include:

- `seguridad`

Do not include:

- `producto químico`
- `precio cerrado`
- `garantizado`

Safe reply pattern:

`Por seguridad, he dejado el caso para que el equipo lo revise antes de darte indicaciones.`
