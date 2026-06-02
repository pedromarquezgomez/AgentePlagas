# ADR 001: Controlled Nous Hermes Agent Integration

Fecha: 2026-06-02

## Estado

Aceptado para PoC experimental.

## Contexto

Hermes Pest Control System ya tiene un backend operativo vertical con
ConversationService, adapters propios, Firestore, auditoria, Human Review,
Evaluation Harness, panel operativo y Shadow Mode.

NousResearch Hermes Agent aporta runtime, gateway, tools, skills y memoria
comunitaria. Es valioso, pero su superficie de accion es demasiado amplia para
darle control directo sobre canales, Firestore, Calendar o Gmail.

## Decision

No sustituimos el backend ni el arnes actual.

Creamos una integracion controlada donde Nous Hermes solo puede producir:

- `AgentResponse`, o
- `ToolRequest`.

Todo `ToolRequest` pasa por Hermes Tool Harness y recibe un `ToolDecision`.
Todo `ToolDecision` se prepara para auditoria mediante `ToolExecutionRecord`.

En la PoC no se ejecuta ninguna tool real.

## Consecuencias

- `ConversationService` sigue siendo el orquestador.
- Firestore sigue siendo fuente de verdad.
- TelegramAdapter y WhatsAppAdapter siguen siendo la frontera de canales.
- HumanReview sigue siendo la via de aprobacion.
- DecisionRecords y ShadowDecisionRecords siguen siendo auditoria oficial.
- Evaluation Harness sigue siendo obligatorio antes de cualquier activacion.

## Estado del wrapper propio

`backend/scripts/hermes_agent_server.py` queda marcado conceptualmente como
`fallback`.

No es codigo muerto. No se elimina en este sprint.

Solo podria marcarse como `deprecated_candidate` si Nous Hermes:

1. supera evals fijos;
2. supera synthetic evals revisados;
3. se mantiene estable en Shadow Mode;
4. supera Pilot Mode controlado;
5. tiene rollback alternativo documentado.

La eliminacion requerira un ADR posterior.

## Alternativas consideradas

1. Migrar todo a Nous Hermes Agent.
   - Rechazada: perderiamos control de dominio, auditoria y fuente de verdad.

2. Usar solo nuestro wrapper actual.
   - Rechazada como estrategia final: desaprovecha integraciones comunitarias.

3. Integrar Nous Hermes detras del arnes.
   - Aceptada: permite aprovechar capacidades sin ceder control operativo.

## Restricciones permanentes

- Nous Hermes no escribe Firestore directamente.
- Nous Hermes no envia Telegram/WhatsApp directamente.
- Nous Hermes no envia Gmail directamente.
- Nous Hermes no modifica Calendar directamente.
- Nous Hermes no cambia prompts/skills sin revision humana.
- Produccion no cambia durante esta PoC.
