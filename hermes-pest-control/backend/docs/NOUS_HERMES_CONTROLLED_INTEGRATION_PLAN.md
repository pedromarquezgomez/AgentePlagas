# Nous Hermes Controlled Integration Plan

Fecha: 2026-06-02

## Aclaracion arquitectonica

Este sprint no migra Hermes Pest Control System a Nous Hermes Agent.

El objetivo es crear la base controlada para integrarlo despues. Nous Hermes no
controla Gmail, Calendar, Telegram, WhatsApp, Firestore ni acciones operativas
en esta fase.

Toda integracion futura debe pasar por:

```text
Nous Hermes Agent
-> ToolRequest
-> Tool Harness
-> ToolDecision
-> auditoria
-> ejecucion controlada o revision humana
```

En la PoC no se ejecuta ninguna tool real. Todo output de Nous Hermes se
convierte a `AgentResponse` o `ToolRequest`. Todo `ToolRequest` recibe un
`ToolDecision`. Todo `ToolDecision` queda preparado para auditoria mediante
`ToolExecutionRecord`.

## Que se mantiene como arnes permanente

- `ConversationService` sigue siendo el orquestador.
- Los channel adapters propios siguen normalizando entrada/salida.
- Firestore sigue siendo la fuente de verdad.
- Los servicios de dominio siguen ejecutando acciones operativas.
- `AgentResponse` sigue siendo el contrato obligatorio de decision.
- DecisionRecords, ShadowDecisionRecords y HumanReview siguen siendo el control
  de auditoria y seguridad.
- Evaluation Harness y synthetic evals siguen siendo la puerta de calidad.
- El panel operativo sigue siendo la superficie de revision humana.

## Que podria aportar Nous Hermes Agent

- Runtime LLM alternativo.
- Sistema comunitario de skills.
- Gateway y conectores como referencia o fuente de integraciones futuras.
- Memoria y tools, siempre encapsulados por el Tool Harness.
- Propuestas de acciones: Gmail draft, Calendar proposal, respuestas de canal,
  busquedas o consultas, nunca ejecucion directa en la primera fase.

## Matriz de componentes

| Componente actual | Funcion | Estado | Sustituye Nous | Adaptacion | Riesgo | Decision |
|---|---|---:|---:|---|---|---|
| TelegramAdapter | Normaliza Telegram y envia respuestas | active | No | Mantener propio | Saltarse auditoria si se duplica gateway | keep |
| WhatsAppAdapter | Normaliza WhatsApp y prepara envio | active | No | Mantener propio | Canal real aun no maduro | keep |
| HermesRealClient | Frontera HTTP para agente real | active | No | Podria apuntar a adapter Nous | Contrato invalido o tools libres | wrap_with_harness |
| `hermes_agent_server.py` | Wrapper LLM propio | fallback | Posible despues | Mantener 2 sprints tras alternativa | Quitar rollback | fallback |
| `hermes/skills` | Politica de dominio y contrato | active | No | Portar/inyectar en Nous | Auto-modificacion no revisada | keep |
| Evals fijos | Calidad minima de comportamiento | active | No | Ejecutar contra Nous | Relajar casos por conveniencia | keep |
| Synthetic evals | Comparacion amplia mock vs IA | active | No | Ejecutar contra Nous | Datos sinteticos mal interpretados | keep |
| GoogleCalendarService | Sync opcional de visitas | active | No | Nous solo propone eventos | Evento real no aprobado | keep |
| Futuro Gmail | Canal/tool futuro | experimental | No | Nous propone borradores | Envio no autorizado | wrap_with_harness |
| Panel Evaluacion IA | Revisa shadow decisions | active | No | Podria mostrar ToolDecisions | UI tecnica excesiva | keep |
| Firestore | Fuente de verdad | active | No | Acceso solo via backend | Escritura directa del agente | keep |
| HumanReview | Revision humana | active | No | Recibe decisiones de Tool Harness | Saltar aprobacion | keep |
| DecisionRecords | Auditoria de decision principal | active | No | Registrar runtime Nous si aplica | Auditoria fragmentada | keep |
| ShadowDecisionRecords | Comparacion IA sombra | active | No | Comparar Nous/controlado | Confundir shadow con accion real | keep |

## Estados de codigo

- `active`: pieza productiva actual.
- `experimental`: pieza aislada de laboratorio.
- `fallback`: pieza mantenida para rollback.
- `deprecated_candidate`: pieza candidata a eliminacion futura, nunca inmediata.
- `removed`: pieza retirada tras criterios formales.

En este sprint no se marca ningun componente productivo como `removed`.

## Deprecation plan del wrapper propio

`hermes_agent_server.py` queda como `fallback`, no como codigo muerto.

Solo podria marcarse como `deprecated_candidate` si:

1. Nous Hermes supera evals fijos.
2. Nous Hermes supera synthetic evals con revision cualitativa.
3. Shadow Mode muestra estabilidad durante al menos un sprint.
4. Pilot Mode controlado se aprueba sin incidentes.
5. Existe rollback documentado.

Solo podria eliminarse si:

1. Ha estado al menos 2 sprints como fallback sin uso critico.
2. Hay alternativa probada en local y cloud.
3. El equipo acepta eliminarlo en un ADR nuevo.

## PoC local

La carpeta `backend/experiments/nous_hermes_controlled/` contiene la PoC
experimental:

- `NousHermesRuntimeAdapter`: convierte output simulado de Nous a
  `AgentResponse` o `ToolRequest`.
- `HermesToolHarness`: decide si la tool propuesta se bloquea, se convierte en
  borrador o requiere revision humana.
- `ToolExecutionRecord`: deja trazabilidad sin ejecutar efectos externos.

Casos cubiertos:

- Programar visita: crea `incident.propose_incident`, propuesta Calendar y
  borrador de canal. La incidencia es propuesta, no escritura real.
- Enviar correo: convierte Gmail en borrador/propuesta, nunca envio real.
- WhatsApp con producto quimico: bloquea el mensaje por riesgo alto y no envia
  nada.

Runner local:

```bash
cd backend
python experiments/nous_hermes_controlled/run_controlled_poc.py
```

El runner escribe un reporte local ignorado por Git:

```text
backend/evals/results/nous_hermes_controlled_poc_YYYYMMDD_HHMMSS.json
```

El reporte contiene `ToolRequest`, `ToolDecision` y `ToolExecutionRecord` para
cada caso. Todos los registros deben tener `executed=false` y
`external_effect=false`.

## Feature flags

Todos los flags quedan apagados por defecto:

```env
NOUS_HERMES_ENABLED=false
NOUS_HERMES_MODE=disabled
NOUS_HERMES_TOOLS_ENABLED=false
NOUS_HERMES_ALLOWED_TOOLS=
TOOL_HARNESS_ENFORCEMENT=strict
```

## Criterio de salida de esta fase

- Plan claro de integracion.
- Politica de permisos de herramientas.
- Schemas `ToolRequest`, `ToolDecision`, `ToolExecutionRecord`.
- PoC local experimental sin tools reales.
- Codigo actual clasificado para evitar codigo muerto.
- Cero cambios en produccion.
- Cero ejecucion real de herramientas externas.
