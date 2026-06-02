# Hermes Product Policy

This document defines the reviewed product behavior for Hermes Pest Control
intake before Pilot Mode. It is a policy reference for prompts, fixed evals,
shadow comparisons, and human review. It does not activate `HERMES_MODE=real`
and it does not grant the LLM permission to write operational data directly.

## Operating Boundary

The system of record remains the backend:

- `ConversationService` orchestrates decisions.
- Hermes returns only `AgentResponse`.
- The backend creates incidents, review items, visits, documents, and audit
  records.
- Telegram, WhatsApp, and the panel are not controlled directly by the LLM.
- Production remains in `HERMES_MODE=mock` until reviewed activation criteria
  are met.

## Allowed Actions

Hermes may choose only these action types:

- `reply_only`
- `collect_missing_data`
- `create_incident`
- `escalate_to_human`

Normal intake requires:

- `pest_type`
- `affected_area`
- `location`

If these three fields are present and no escalation trigger exists, the expected
action is `create_incident`.

If one or more fields are missing and no escalation trigger exists, the expected
action is `collect_missing_data`. Known fields should still be preserved.

If an escalation trigger exists, the expected action is `escalate_to_human`,
even if required fields are incomplete.

## Pest Extraction Policy

Supported normalized pest values:

- `cucarachas`
- `roedores`
- `hormigas`
- `chinches`
- `avispas`

Common mappings:

- rats, mice, `ratas`, `ratones`, `roedor`, `roedores` -> `roedores`
- `chinche`, `chinches`, `chinches de cama` -> `chinches`
- `avispa`, `avispas`, `nido de avispas` -> `avispas`

If the pest is unclear, use `pest_type=null` and ask for `pest_type`.

## Field Extraction Policy

`location` is the locality or town only, for example:

- `Torremolinos`
- `Málaga`
- `Marbella`
- `Fuengirola`
- `Benalmádena`

`affected_area` is the operational zone, for example:

- `cocina`
- `garaje`
- `baño`
- `jardín`
- `almacén`
- `dormitorio`
- `terraza`

Do not put business type, room, or extra context inside `location`.

## Priority Policy

Use `urgent` for:

- possible intoxication;
- real chemical/product exposure;
- pets exposed to products;
- pets present in a property when there is a direct product exposure or unsafe
  pest/product handling context;
- babies, children, elderly people, pregnant people, respiratory-risk people,
  or other vulnerable people at risk;
- active pests in restaurants, bars, food businesses, or food-handling kitchens;
- wasp nests or repeated wasp activity near living areas when children,
  vulnerable people, or immediate safety concern are mentioned;
- chinches with bites plus health concern or vulnerable people.

Use `high` for:

- `cucarachas`;
- `roedores`;
- `chinches`;
- roedores reported indoors even when no immediate health emergency is
  described;
- avispas near living areas without vulnerable-person signal;
- angry customers, complaints, reclamations, or legal pressure;
- requests for chemical products or application instructions without exposure;
- fixed, final, closed price requests without enough operational review;
- total guarantee demands.

Use `medium` for ordinary lower-risk cases such as ants when there is no
vulnerable person, food business, chemical exposure, or urgent signal.

Use `low` only when the user clearly describes a minor, non-urgent issue.

## Escalation Policy

Escalate to human review for:

- possible intoxication;
- chemical exposure;
- pet exposure;
- vulnerable people at risk;
- pets exposed to products or clearly at risk from unsafe product handling;
- food-business critical context;
- requests for poison, pesticide, biocide, product names, doses, application, or
  mixing instructions;
- fixed/closed/final price or guarantee pressure;
- very angry customers, complaints, reclamations, or legal threats;
- unsupported or ambiguous safety-sensitive requests.

Escalation usually still sets `incident.should_create=true` so operations can
review the case.

## Price Policy

Hermes must not invent:

- exact price;
- final price;
- closed price;
- guaranteed result.

When the user asks for a firm price without review, use `escalate_to_human`
with `priority="high"` and safe wording. Do not include the phrase
`precio cerrado` in the user-facing reply.

## Chemical And Safety Policy

Hermes must not provide:

- product recommendations;
- pesticide or biocide names;
- doses;
- application steps;
- mixing instructions;
- cleaning/exposure instructions;
- medical or veterinary advice.

When there is only a product/application question, escalate with high priority.
When there is actual exposure, symptoms, pets, vulnerable people, or food
business risk, escalate with urgent priority.

Avoid these user-facing terms:

- `producto químico`
- `precio cerrado`
- `garantizado`
- `veneno`

## Typo And Noisy Input Policy

Hermes may correct obvious Spanish spelling mistakes when the meaning is
high-confidence:

- `cucaraxa` -> `cucarachas`
- `cosina` -> `cocina`
- `ormigas` -> `hormigas`
- `jardin` -> `jardín`
- `malaga` -> `Málaga`

If pest, affected area, and locality are all clear despite typos, create an
incident unless escalation is required.

If any required field is uncertain, preserve clear fields and ask only for the
missing or uncertain fields.

## Fixed Eval Policy

Cases promoted from synthetic analysis may be scoped by Hermes mode:

- default cases apply to both mock and real unless specified otherwise;
- pilot policy cases may use `"hermes_modes": ["real"]` to evaluate the LLM
  candidate without changing the production mock baseline.

This prevents new LLM policy criteria from breaking the V1 mock flow while
still making the target behavior explicit.

Current fixed-eval coverage:

- `backend/evals/cases/pest_escalation_cases.json` covers pet exposure and food
  business escalation.
- `backend/evals/cases/safety_cases.json` covers product, mixing, guarantee,
  and fixed-price safety boundaries.
- `backend/evals/cases/pilot_policy_cases.json` covers the Sprint 21 pilot
  criteria for chinches, vulnerable people, wasps, angry/reclamation cases,
  typo tolerance, incomplete messages, price requests, and chemical exposure.

## Pilot Mode Gate

Before any controlled Pilot Mode activation:

- `make evals` must pass in mock mode;
- LLM-specific evals must be reviewed by humans;
- synthetic shadow reports must show no transport/fallback instability;
- differences must be classified as `llm_better`, `mock_better`,
  `ambiguous_needs_policy`, or `eval_case_needs_refinement`;
- fallback and Human Review must remain active;
- Telegram must not be switched to real LLM behavior without explicit approval.
