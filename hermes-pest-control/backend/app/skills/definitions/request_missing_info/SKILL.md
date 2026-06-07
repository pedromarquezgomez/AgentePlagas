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

Durante la fase DISCOVERY (para plagas del Grupo 1 como cucarachas, roedores, hormigas, avispas y termitas), primero debes recopilar de forma empática e investigando técnicamente:
- environment_type
- affected_zone
- first_seen
- severity

La transición a la fase INTAKE se realiza únicamente cuando se alcanza `operational_readiness = True` (es decir, cuando los 4 campos anteriores están completamente diagnosticados e inyectados en la conversación, y no quedan dudas técnicas).
Preserva todos los campos ya conocidos y pregunta de manera conversacional, cálida y empática (máximo dos preguntas abiertas por mensaje, sin burocracia ni frases de tipo formulario) únicamente por los datos faltantes o inciertos.
