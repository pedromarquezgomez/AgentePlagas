---
name: summarize_case
description: Summarize the case for operators or draft documents.
allowed_outputs:
  - summary
  - reply
  - document_draft
forbidden_effects:
  - document_persist
  - database_write
  - channel_send
risk_level: low
requires_backend_service: true
---
Genera un resumen operativo descriptivo y estructurado del caso para que el técnico de control de plagas tenga todo el contexto de la situación.
El agente no debe persistir documentos directamente en la base de datos ni emitir certificados legales o comerciales oficiales.
