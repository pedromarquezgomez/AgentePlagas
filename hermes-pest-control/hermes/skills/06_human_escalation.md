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
- babies, small children, elderly people, respiratory-risk people, or other
  vulnerable people in the same property when an interior pest is reported;
- restaurant, bar, food business, kitchen in a food business, or critical food
  handling context;
- chinches with reported bites, strong health concern, or vulnerable people;
- wasp nest or repeated wasp activity near living areas when there are children,
  vulnerable people, or immediate safety concern;
- user asks what chemical product to use;
- user asks whether to mix products, bleach, ammonia, or similar substances;
- user demands a total guarantee;
- user demands a fixed/closed price without enough operational data;
- user is very angry, threatens complaint/reclamation/legal action, or
  explicitly asks for review by a person.

Escalation does not mean `incident.should_create=false`. For most escalation
cases, create an incident so the team can review it.

Use `priority="urgent"` for:

- possible intoxication;
- pet or vulnerable-person exposure;
- vulnerable people with interior pest risk;
- food-business critical risk;
- restaurant/bar/kitchen business with active pest report.
- wasp nests near living areas when children or vulnerable people are present.

Use `priority="high"` for:

- angry customer or complaint;
- complaint/reclamation/legal pressure involving roedores, cucarachas, or other
  active pest reports;
- chemical/product request without exposure symptoms;
- product-mixing request;
- guarantee or fixed-price pressure;
- roedores, cucarachas, chinches, or avispas when no immediate health emergency
  is described.

Do not mark a chemical/product question as `urgent` just because the user asks
what to use. It becomes `urgent` only when the user reports exposure,
intoxication symptoms, pets, vulnerable people, or food-business critical risk.

Do not escalate or mark `urgent` solely because the pest is `chinches` in a
bedroom. If the message has pest, affected area, and locality, and there are no
bites, vulnerable people, strong health concern, or high affectation, use
`create_incident` with `priority="high"`.

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
