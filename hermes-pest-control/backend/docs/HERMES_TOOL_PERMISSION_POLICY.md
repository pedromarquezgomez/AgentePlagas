# Hermes Tool Permission Policy

Fecha: 2026-06-02

## Principio central

Nous Hermes Agent puede proponer acciones, pero no ejecutarlas directamente.

Toda accion externa debe pasar por:

```text
ToolRequest -> Tool Harness -> ToolDecision -> auditoria -> ejecucion controlada o revision humana
```

En la PoC no hay ejecucion real de herramientas externas.

## Niveles de permiso

| Nivel | Nombre | Descripcion | Ejecucion en PoC |
|---:|---|---|---|
| 0 | Lectura/propuesta | Consultas o propuestas sin efecto externo | No ejecuta |
| 1 | Borrador | Crear borradores internos revisables | Convertido a propuesta |
| 2 | Accion segura | Accion de bajo riesgo, reversible y acotada | No ejecuta |
| 3 | Accion con aprobacion | Efecto externo o comunicacion con cliente | Revision humana |
| 4 | Autonomia limitada | Ejecucion con limites y supervision | No permitido |
| 5 | No permitido todavia | Riesgo alto o acceso directo a fuente de verdad | Denegado |

## Politicas por herramienta

### Gmail

| Accion | Nivel | Decision inicial |
|---|---:|---|
| Leer correo autorizado | 0 | Propuesta futura, no PoC |
| Crear borrador | 1 | `convert_to_draft`; ejecutable solo tras aprobacion |
| Enviar correo | 3 | `deny` en PoC |
| Enviar correo sensible | 5 | `deny` hasta nueva policy |

Regla: Nous no envia emails. Como maximo propone borradores revisables. Desde
Sprint 25, un operador puede ejecutar `gmail.create_draft` tras aprobar la
accion, siempre que los flags de Gmail esten activos. `gmail.send_email` sigue
bloqueado.

### Incidencias internas

| Accion | Nivel | Decision inicial |
|---|---:|---|
| Proponer incidencia | 1 | `allow` como propuesta no ejecutada |
| Crear incidencia directa | 5 | `deny` si intenta escribir fuera del backend |

Regla: una propuesta de incidencia puede formar parte del resultado
experimental, pero la escritura real solo puede ocurrir por servicios internos
del backend productivo.

### Calendar

| Accion | Nivel | Decision inicial |
|---|---:|---|
| Leer disponibilidad | 0 | Propuesta futura, no PoC |
| Proponer evento | 1 | `require_human_approval` |
| Crear evento | 3 | `require_human_approval` |
| Cancelar evento | 5 | `deny` |

Regla: Firestore/VisitService sigue siendo fuente de verdad. Calendar externo es
integracion secundaria.

### Telegram y WhatsApp

| Accion | Nivel | Decision inicial |
|---|---:|---|
| Borrador de respuesta | 1 | `require_human_approval` |
| Confirmacion simple en Pilot Mode | 2 | Futuro, no PoC |
| Caso sensible | 3 | `require_human_approval` |
| Mensaje proactivo | 3 | `require_human_approval` |
| Consejo quimico/fumigacion | 5 | `deny` |

Regla: Nous no envia mensajes por canales. Los adapters propios siguen siendo
la unica salida real.

### Firestore

| Accion | Nivel | Decision inicial |
|---|---:|---|
| Lectura controlada via backend | 0 | Futuro, no PoC |
| Escritura directa | 5 | `deny` |
| Crear incidencia directa | 5 | `deny` |
| Modificar visitas/tecnicos/documentos directo | 5 | `deny` |

Regla: cualquier accion de dominio debe pasar por servicios internos, nunca por
tools directas del agente.

## Reglas de enforcement

- `TOOL_HARNESS_ENFORCEMENT=strict` es el unico modo soportado en la PoC.
- `NOUS_HERMES_TOOLS_ENABLED=false` bloquea todo.
- `NOUS_HERMES_ALLOWED_TOOLS` debe enumerar tools permitidas para cualquier
  decision distinta de `deny`.
- Ninguna decision de la PoC produce `executed=true`.
- Ningun `ToolExecutionRecord` de la PoC puede tener `external_effect=true`.
- La revision humana puede cambiar `review_status`, `reviewer_notes`,
  `reviewed_by` y `approved_payload`.
- `review_status=approved` no implica ejecucion. Solo deja constancia de que la
  propuesta podria pasar a una fase futura de ejecucion controlada.

## Politicas iniciales implementadas

- Incident proposal `incident.propose_incident` -> `allow` como propuesta no
  ejecutada.
- Gmail `create_draft` -> `convert_to_draft`.
- Gmail `send_email` -> `deny`.
- Calendar `propose_event` o `create_event` -> `require_human_approval`.
- Telegram/WhatsApp draft/message -> `require_human_approval`.
- WhatsApp/Telegram con consejo quimico o fumigacion -> `deny`.
- Firestore directo -> `deny`.
- Tool no allowlisted -> `deny`.
- Tools desactivadas por flag -> `deny`.

## Revision operativa

Los registros de herramientas se consultan en:

```text
GET /tools/executions
GET /tools/executions/{id}
PATCH /tools/executions/{id}
```

Estados de revision:

| Estado | Uso |
|---|---|
| `proposed` | Propuesta recibida, pendiente de revisar |
| `approved` | Revisada y aceptada como propuesta, sin ejecucion real |
| `rejected` | Rechazada por politica o criterio operativo |
| `needs_more_info` | Falta informacion para decidir |
| `dismissed` | Descartada sin accion |

Campos editables:

- `review_status`
- `reviewer_notes`
- `reviewed_by`
- `approved_payload`

Campos no editables desde revision:

- `executed`
- `external_effect`
- `tool_name`
- `provider`
- `action`
- `decision`
- `execution_status`

Aprobar una accion IA no ejecuta por si mismo. Desde Sprint 25 existe una
accion separada de ejecucion controlada para `gmail.create_draft`; calendario,
mensajes por canales, `gmail.send_email` y escritura directa en Firestore siguen
bloqueados.

## Ejecucion Gmail draft

Endpoint protegido:

```text
POST /tools/executions/{id}/execute
```

Solo se permite:

```text
tool_name=gmail.create_draft
provider=gmail
action=create_draft
review_status=approved
executed=false
```

Flags obligatorios:

```text
GMAIL_TOOLS_ENABLED=true
GMAIL_DRAFT_EXECUTION_ENABLED=true
```

Payload requerido:

```json
{
  "recipient": "cliente@example.test",
  "subject": "Resumen",
  "body": "Texto del borrador"
}
```

Resultado auditado:

- `executed=true`
- `external_effect=true`
- `execution_status=executed`
- `execution_result.provider=gmail`
- `execution_result.draft_id`
- `execution_result.message_id`

El resultado no debe guardar el cuerpo completo del email. El sistema crea
borrador, no envia correo.
