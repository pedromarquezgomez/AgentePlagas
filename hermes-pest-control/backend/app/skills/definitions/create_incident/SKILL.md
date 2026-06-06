---
name: create_incident
description: Propose an incident when intake is complete and safe.
allowed_outputs:
  - action.create_incident
  - incident
forbidden_effects:
  - database_write
  - direct_firestore_write
risk_level: medium
requires_backend_service: true
---
Devuelve únicamente una propuesta de creación en AgentResponse.
El servicio de backend IncidentService y el arnés de políticas de ejecución son los únicos autorizados para persistir y crear la incidencia en la base de datos real.
