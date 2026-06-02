# NousResearch Hermes Agent Integration Study

Fecha: 2026-06-02

Repositorio evaluado: https://github.com/nousresearch/hermes-agent

## Resumen ejecutivo

NousResearch Hermes Agent puede complementar nuestro arnes como runtime de IA o como referencia de capacidades, pero no debe sustituir el backend operativo de Hermes Pest Control System.

La opcion mas razonable para una prueba controlada es usar Nous Hermes Agent como runtime LLM detras de `HermesRealClient`, manteniendo:

- `ConversationService` como orquestador.
- `AgentResponse` como contrato obligatorio.
- `DecisionRecords`, `ShadowDecisionRecords`, fallback seguro y Human Review.
- Firestore como fuente de verdad.
- Telegram/WhatsApp adapters propios como capa de canal.

No se recomienda delegar canales, agenda, documentos, Firestore ni acciones operativas directamente a Nous Hermes en esta fase. La superficie de herramientas de Nous Hermes es potente, pero demasiado amplia para activarla sin un modelo de permisos estricto.

## Alcance

Este estudio analiza si `nousresearch/hermes-agent` puede sustituir o complementar el wrapper LLM propio actual.

No se ha hecho migracion, no se ha tocado produccion, no se ha activado `HERMES_MODE=real` y no se ha conectado Telegram a Nous Hermes.

## Fuentes revisadas

Se clono el repositorio en un entorno temporal aislado:

```bash
git clone --depth 1 https://github.com/nousresearch/hermes-agent.git /tmp/nous-hermes-agent
```

Version observada en `pyproject.toml`:

```text
hermes-agent 0.15.1
requires-python >=3.11
```

Puntos relevantes verificados en el repositorio:

- CLI principal `hermes`.
- Entrada alternativa `hermes-agent`.
- Gateway de mensajeria.
- API server compatible con OpenAI.
- Sistema de skills.
- Memoria persistente.
- Cron/automatizaciones.
- Toolsets configurables.
- Adaptadores de canal como Telegram, WhatsApp y Email.

Documentacion publica relevante:

- https://hermes-agent.nousresearch.com/docs/
- https://hermes-agent.nousresearch.com/docs/user-guide/cli
- https://hermes-agent.nousresearch.com/docs/user-guide/messaging
- https://hermes-agent.nousresearch.com/docs/user-guide/features/tools
- https://hermes-agent.nousresearch.com/docs/user-guide/features/skills
- https://hermes-agent.nousresearch.com/docs/user-guide/features/memory
- https://hermes-agent.nousresearch.com/docs/user-guide/features/cron
- https://hermes-agent.nousresearch.com/docs/developer-guide/programmatic-integration

## Prueba local aislada

Se creo un entorno virtual temporal dentro del clon, sin instalar nada global:

```bash
cd /tmp/nous-hermes-agent
uv venv .venv-study --python 3.12
uv pip install --python .venv-study/bin/python -e .
```

Resultado: instalacion editable completada correctamente.

Se verifico la superficie CLI:

```bash
.venv-study/bin/hermes --help
.venv-study/bin/hermes gateway --help
```

Hallazgos:

- El CLI soporta `-z/--oneshot` para invocaciones de una sola respuesta.
- Soporta override de modelo/proveedor mediante `--model` y `--provider`.
- Soporta toolsets mediante `--toolsets`.
- Soporta skills mediante `--skills`.
- El gateway puede ejecutarse en foreground o como servicio.

No se ejecuto un prompt real contra proveedor LLM en esta prueba porque no se configuraron credenciales en el entorno temporal y no era necesario para evaluar la arquitectura de integracion.

## Capacidades relevantes de Nous Hermes Agent

### Instalacion local

El paquete puede instalarse como proyecto Python. El repositorio usa dependencias core exact-pinned y extras opcionales para canales y capacidades. Esto es positivo desde el punto de vista de reproducibilidad, aunque el conjunto completo de extras tiene una superficie amplia.

### CLI

El CLI `hermes` ofrece modo interactivo y modo oneshot:

```bash
hermes -z "prompt"
```

Este modo podria usarse como adaptador simple, pero no es la opcion preferida para nuestro sistema porque:

- Capturar errores estructurados es mas dificil que con HTTP.
- El stdout final no garantiza por si solo `AgentResponse`.
- El proceso podria cargar reglas, memoria o herramientas segun configuracion local.
- Es menos natural para Cloud Run que un servicio HTTP.

### Gateway

El gateway permite conectar canales como Telegram, WhatsApp, Slack, Discord y otros. Tambien expone un API server.

Para nuestro proyecto, el gateway de canales no debe reemplazar los adapters propios en esta fase. Nuestros adapters ya normalizan mensajes hacia `IncomingMessage`, mantienen el flujo por `ConversationService` y preservan auditoria, persistencia y reglas de negocio.

### API server HTTP

El archivo `gateway/platforms/api_server.py` expone endpoints estilo OpenAI, entre otros:

- `POST /v1/chat/completions`
- `POST /v1/responses`
- `GET /v1/responses/{response_id}`
- `GET /v1/models`
- `GET /v1/capabilities`
- `GET /v1/toolsets`
- `GET /health`
- `GET /health/detailed`

El API server requiere `API_SERVER_KEY` y rechaza arrancar sin clave. Esto es positivo para un servicio separado, pero no equivale aun a nuestro contrato `/agent`. Haria falta un adaptador que:

1. Construya prompt con nuestras skills y policy.
2. Llame a Nous Hermes API server.
3. Extraiga JSON.
4. Valide `AgentResponse`.
5. Devuelva error controlado si falla.

### Skills

Nous Hermes trae un sistema de skills y auto-mejora. Nuestro proyecto ya tiene skills/policies de control de plagas en Markdown bajo `hermes/skills`.

Posible encaje:

- Portar nuestras skills como skills estaticas.
- Usar Nous como runtime que consume esas instrucciones.
- Desactivar auto-modificacion de skills durante pilotos operativos.

Riesgo:

- La auto-mejora puede ser util en laboratorio, pero no debe cambiar policy de producto sin revision humana.

### Tools

Nous Hermes tiene toolsets amplios: terminal, procesos, archivos, busqueda web, vision, memoria, cron, envio de mensajes, delegacion, MCP y otros.

Para Hermes Pest Control System, estos tools deben estar desactivados o muy restringidos inicialmente. El agente no debe tener permisos para:

- Escribir en Firestore.
- Enviar Telegram/WhatsApp.
- Crear visitas, documentos o tecnicos.
- Ejecutar comandos de sistema.
- Modificar prompts/skills sin revision.

### Memoria

Nous Hermes soporta memoria y session search. Nuestro sistema ya tiene Firestore, conversaciones, mensajes, DecisionRecords y ShadowDecisionRecords.

Recomendacion:

- No usar memoria persistente de Nous para datos de clientes en la primera integracion.
- Pasar `conversation_history` desde nuestro backend.
- Mantener Firestore como fuente de verdad.

### Cambio de modelos

Nous Hermes permite configurar proveedor/modelo desde CLI/config. Es util para laboratorio, pero en produccion debe estar fijado por variables controladas y auditado por nuestro sistema.

### Invocacion programatica

Opciones detectadas:

1. CLI oneshot.
2. API server OpenAI-compatible.
3. Importar libreria Python internamente.
4. Gateway/canales.

Recomendacion tecnica: API server o wrapper HTTP propio alrededor de Nous Hermes. Evitar importacion directa en el backend principal para no acoplar dependencias, config global, memoria ni tools al proceso operativo.

## Matriz comparativa

| Componente | Nuestro sistema actual | Nous Hermes Agent | Posible integracion | Riesgo | Recomendacion |
|---|---|---|---|---|---|
| Canal Telegram | `TelegramAdapter`, webhook propio, sin logica de negocio | Gateway Telegram completo con envio/recepcion | Usarlo solo en laboratorio o referencia | Duplicar canales y saltar auditoria | Mantener adapter propio |
| WhatsApp | Adapter propio preparado/mock | Gateway WhatsApp disponible con bridge/config | Referencia tecnica para evolucionar adapter | Dependencias externas y permisos de envio | Mantener adapter propio |
| Gmail | No implementado como canal operativo | Puede integrarse por gateway/tools/skills | Futuro canal investigable | PII, autorizaciones OAuth, acciones autonomas | Evaluar separado, no ahora |
| Calendar | Google Calendar opcional desde VisitService | Puede operar con tools/skills/cron segun configuracion | Solo referencia para automatizaciones | Que el agente modifique agenda | Mantener GoogleCalendarService propio |
| Skills | Markdown de producto y seguridad | Sistema de skills, hub y auto-mejora | Portar nuestras skills como contexto/runtime | Auto-modificacion no revisada | Usar skills estaticas, revisar cambios manualmente |
| Memoria | Firestore, conversation history, audit records | Memoria persistente y session search | Pasar history desde nuestro backend | Retencion de PII fuera de Firestore | Desactivar o aislar al inicio |
| Tools | Backend controla acciones por servicios | Toolsets amplios: terminal, file, web, cron, send_message, etc. | Toolsets minimo o ninguno | Prompt injection y acciones peligrosas | No habilitar tools operativos al inicio |
| Cambio de modelos | Variables del wrapper LLM | CLI/config por proveedor/modelo | Runtime experimental en shadow/evals | Drift no auditado | Fijar modelo por entorno y registrar modo |
| Subagentes | No usado en V1 | Delegacion/subagentes disponible | Investigacion futura | Dificil auditar decisiones | No usar en piloto de negocio |
| Automatizaciones | No autonomas; endpoints/servicios manuales | Cron integrado y delivery a canales | Referencia futura | Acciones sin supervision | No usar para acciones de clientes |
| Evaluacion | Evals fijos, synthetic evals, shadow mode | No sustituye nuestro evaluation harness | Evaluar Nous contra nuestro harness | Metricas incompatibles si se separa | Mantener harness propio |
| Control de acciones | `ConversationService` + servicios de dominio | Agent tools pueden actuar directamente | Limitar Nous a decision textual JSON | Saltarse reglas de negocio | No dar tools de escritura/envio |
| Auditoria | DecisionRecords, ShadowDecisionRecords | Logs/sesiones propias | Registrar salida Nous en nuestro audit | Auditoria fragmentada | Nuestro audit sigue siendo oficial |
| Fallback | Fallback seguro `escalate_to_human` | Errores propios del runtime | Adaptador convierte errores a fallback | Fallback opaco si no se normaliza | Mantener fallback nuestro |
| Human Review | Cola operativa propia | No equivalente directo | Crear review desde nuestra decision/fallback | Saltar revision humana | Mantener HumanReviewService |
| Firestore | Fuente de verdad | Sin integracion de dominio | Ninguna directa | Escrituras no controladas | Nous no escribe Firestore |

## Opciones de integracion

### Opcion A: mantener wrapper propio y usar Nous como referencia

Consiste en mantener nuestro `hermes_agent_server.py` actual y estudiar Nous para mejorar:

- Tool permissions.
- Gateway patterns.
- Skills.
- API server.
- Observabilidad.
- Memoria y sesiones.

Ventajas:

- Riesgo muy bajo.
- No se toca produccion.
- No se introduce una dependencia compleja.
- Conserva todos los tests y evals actuales.

Inconvenientes:

- No aprovechamos directamente el runtime de Nous.
- El wrapper propio sigue siendo responsabilidad nuestra.

Recomendacion: buena opcion inmediata si el objetivo es consolidar V1 y aprender.

### Opcion B: usar Nous Hermes Agent como runtime LLM detras de HermesRealClient

Consiste en crear un servicio aislado que use Nous Hermes Agent y exponga un endpoint compatible con nuestro `/agent` o un adaptador que llame al API server OpenAI-compatible.

Flujo propuesto:

```text
ConversationService
-> HermesService
-> HermesRealClient
-> HTTP /agent adapter
-> Nous Hermes Agent runtime
-> JSON AgentResponse validado
```

Reglas:

- Nous solo propone `AgentResponse`.
- No tiene tools de escritura.
- No envia mensajes.
- No accede a Firestore.
- No se activa como principal.
- Primero se ejecuta en evals y shadow mode.

Ventajas:

- Encaja con nuestro arnes.
- Permite comparar Nous vs wrapper actual.
- Mantiene auditoria y fallback.
- Puede aprovechar API server, skills y modelo de runtime.

Inconvenientes:

- Requiere adaptar OpenAI-compatible response a `AgentResponse`.
- Hay que controlar muy bien toolsets, memoria y prompts.
- Se introduce un proceso/dependencia adicional.

Recomendacion: opcion preferida para el siguiente spike tecnico, solo en laboratorio/shadow.

### Opcion C: usar Nous Hermes Gateway/canales para conectores y mantener nuestro sistema como orquestador

Consiste en usar gateway/canales de Nous para algunos conectores como Gmail, Slack o canales no existentes, reenviando eventos a nuestro backend.

Ventajas:

- Puede acelerar conectores futuros.
- Gateway ya trae mucha infraestructura.

Inconvenientes:

- Riesgo de duplicar nuestra capa `IncomingMessage`/`OutgoingMessage`.
- Puede saltarse auditoria si no se encapsula bien.
- Los canales con tools de envio son delicados.

Recomendacion: no usar para Telegram/WhatsApp actuales. Considerarlo solo para conectores nuevos y con un bridge que entregue eventos normalizados al backend.

## Riesgos de seguridad

1. Prompt injection desde canales reales.
   - Un cliente podria intentar inducir al agente a ignorar reglas o ejecutar tools.
   - Mitigacion: no dar tools de escritura/envio y validar `AgentResponse`.

2. Superficie de herramientas amplia.
   - Terminal, archivos, cron, web y send_message no deben estar disponibles en el runtime de negocio.
   - Mitigacion: toolsets minimos, preferiblemente sin tools al inicio.

3. Memoria y PII.
   - Datos de clientes pueden quedar en memoria del runtime si se activa memoria persistente.
   - Mitigacion: desactivar memoria o aislarla; Firestore sigue como fuente oficial.

4. Auto-mejora de skills.
   - Cambios automaticos pueden alterar politica de producto.
   - Mitigacion: no autoescribir skills; promocion manual y revisada.

5. Canales duplicados.
   - Gateway Telegram/WhatsApp podria responder sin pasar por nuestro `ConversationService`.
   - Mitigacion: no configurar tokens de canales en Nous para pilotos de negocio.

6. Exposicion HTTP.
   - API server puede ejecutar trabajo de agente y requiere clave.
   - Mitigacion: `API_SERVER_KEY`, Cloud Run privado si procede, allowlist/red interna, logs sin secretos.

7. Drift de modelo/config.
   - Cambios de modelo pueden alterar decisiones.
   - Mitigacion: registrar modelo/modo en `DecisionRecord` o `ShadowDecisionRecord`.

## Encaje recomendado en nuestro arnes

El arnes que no debe perderse:

- Channel adapters propios.
- `IncomingMessage` / `OutgoingMessage`.
- `ConversationService`.
- `HermesService`.
- `AgentResponse`.
- Validacion Pydantic.
- Fallback seguro.
- DecisionRecords.
- HumanReview.
- Firestore/MockFirestore.
- Evaluation Harness.
- Panel operativo y Evaluacion IA.

Nous Hermes puede entrar solo en el bloque de runtime IA:

```text
HermesRealClient -> NousRuntimeAdapter -> Nous Hermes Agent
```

El resultado debe volver siempre como `AgentResponse` validado.

## Spike tecnico recomendado

Fase 1: laboratorio local

1. Crear un servicio `nous_hermes_agent_server.py` aislado.
2. Ejecutarlo con `API_SERVER_ENABLED=true` o invocacion CLI controlada.
3. No configurar Telegram/WhatsApp/Gmail.
4. No habilitar tools de escritura/envio.
5. Pasar prompt con nuestras skills y contrato.
6. Validar salida `AgentResponse`.
7. Ejecutar `make evals-agent-llm` equivalente.

Fase 2: shadow mode cloud

1. Desplegar servicio separado.
2. Protegerlo con API key.
3. Configurar solo `HERMES_SHADOW_API_URL`.
4. Mantener `HERMES_MODE=mock`.
5. Comparar con `ShadowDecisionRecords`.

Fase 3: decision de producto

1. Revisar diferencias cualitativas.
2. Promocionar casos a evals fijos.
3. Ajustar policy/skills manualmente.
4. No activar como agente principal hasta superar evals y pilotos internos.

## Decision preliminar

NousResearch Hermes Agent puede encajar como runtime experimental detras de nuestro `HermesRealClient`, pero solo si se encapsula. No debe convertirse en el orquestador operativo del negocio.

Recomendacion final:

- Corto plazo: Opcion A para aprendizaje y referencia.
- Siguiente spike: Opcion B, usando servicio separado y shadow mode.
- Evitar por ahora: Opcion C para Telegram/WhatsApp existentes.

## Estado de produccion

Sin cambios.

- Backend principal sigue con `HERMES_MODE=mock`.
- Telegram real no usa Nous Hermes.
- Firestore real no es accesible directamente por Nous Hermes.
- No se han versionado secretos.
- No se ha hecho deploy.

