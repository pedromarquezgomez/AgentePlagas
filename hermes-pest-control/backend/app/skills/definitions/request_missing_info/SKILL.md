---
name: request_missing_info
description: Ask only for the operational fields still missing.
allowed_outputs:
  - reply
  - action.collect_missing_data
  - missing_fields
forbidden_effects:
  - database_write
  - channel_send
  - tool_execution
risk_level: low
requires_backend_service: true
---
Los campos de admisión (intake) requeridos para registrar el servicio final son:
- customer_name
- location
- pest_type

Durante la fase DISCOVERY (para plagas del Grupo 1 como cucarachas, roedores, hormigas, avispas y termitas), primero debes recopilar obligatoriamente:
- environment_type
- affected_zone
- first_seen
- severity

Antes de poder transicionar a la fase INTAKE.
Preserva todos los campos ya conocidos y pregunta de manera conversacional y empática únicamente por los datos faltantes o inciertos.
