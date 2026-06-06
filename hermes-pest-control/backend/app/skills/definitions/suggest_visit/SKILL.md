---
name: suggest_visit
description: Suggest that a visit may be needed without scheduling it.
allowed_outputs:
  - reply
  - tool_request.propose_calendar_event
forbidden_effects:
  - calendar_write
  - visit_write
  - technician_assignment
risk_level: medium
requires_backend_service: true
---
El agente puede sugerir la posibilidad de programar una visita técnica presencial del técnico de plagas al cliente o redactar un borrador de evento.
La asignación definitiva de técnicos y la programación o modificación de la agenda es facultad exclusiva de VisitService y de la aprobación final del operador humano.
