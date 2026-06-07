# Architecture Decision Record (ADR): Consolidación de Autoridad Conversacional (Sprint 34)

## Contexto y Problema

Durante los Sprints 31, 32 y 33, el agente conversacional Hermes experimentó una rápida expansión funcional. Sin embargo, una auditoría arquitectónica reveló un problema de acoplamiento y dispersión de lógica conversacional en el que múltiples componentes influían simultáneamente en la toma de decisiones:
* `DiagnosticEngine` y `ConversationService` duplicaban la extracción de variables técnicas (`environment_type`, `affected_zone`, `severity`, `first_seen`).
* Las reglas de seguridad y revisión humana (`safety_terms` y `review_terms`) estaban duplicadas tanto en `DiagnosticEngine` como en `HermesMockClient`.
* El `HermesMockClient` contenía lógica duplicada de flujos conversacionales (decisiones de preguntas, orden conversacional, descubrimiento de plagas comunes, etc.), lo que requería duplicar cada mejora conversacional para los tests y producción.

Para simplificar el sistema, hacerlo predecible y mantenible, se decidió consolidar toda la autoridad de decisión conversacional en una única fuente de verdad: el `DiagnosticEngine`.

## Decisiones de Diseño

### 1. Centralización en el DiagnosticEngine
El `DiagnosticEngine` es ahora el **único responsable** de dictaminar:
* La fase conversacional (`phase`: `"DISCOVERY"`, `"DIAGNOSIS"`, `"INTAKE"`, `"OUT_OF_DOMAIN"`).
* Los datos técnicos extraídos de descubrimiento (`discovery_data`).
* El siguiente objetivo de la conversación (`next_objective`).
* Si se requiere escalado humano (`escalation_required`).
* La preparación operativa (`operational_readiness`).

Para reflejar esto, el contrato de `DiagnosisAssessment` en `backend/app/diagnostics/contracts.py` fue ampliado con dichos campos estructurados. El motor ya no genera texto ni empatía, solo decisiones de flujo.

### 2. Simplificación del ConversationService
`ConversationService` ha sido despojado de cualquier responsabilidad de extracción de variables, interpretación de texto o lógica de reincidencia. Ahora funciona puramente como un orquestador que:
* Llama a `DiagnosticEngine.assess()` pasándole el contexto de la conversación.
* Actualiza y persiste el estado de la conversación en Firestore basándose únicamente en los datos estructurados del `DiagnosisAssessment`.
* Pasa el `assessment` al runtime/cliente de Hermes a través del contexto empresarial.

### 3. Creación de una SecurityPolicy Unificada
Se ha creado un módulo unificado de seguridad en [security_policy.py](file:///Users/pedro/AgentePlagas%20/hermes-pest-control/backend/app/security/security_policy.py) (`app/security/security_policy.py`). Este componente encapsula de forma única los términos de seguridad y revisión humana, eliminando las listas duplicadas en el sistema. Todos los componentes consumen esta capa única de políticas.

### 4. Mock Client basado en Datos Estructurados
`HermesMockClient` ha sido completamente simplificado. Ya no realiza decisiones conversacionales. Simplemente consume la salida estructurada (`assessment`) proveniente del `DiagnosticEngine` y actúa como un renderizador o generador de respuestas empáticas basándose en el `next_objective` y en la plaga indicada por el motor.

---

## Matriz de Responsabilidad Conversacional Final

A continuación se detalla qué componente tiene la última palabra sobre las decisiones del agente ante un mensaje del usuario (por ejemplo: *"Tengo cucarachas"*):

| Decisión | Componente con Autoridad Final | Rol de los Demás Componentes |
| :--- | :--- | :--- |
| **La Fase Conversacional** | `DiagnosticEngine` | `ConversationService` persiste la fase en Firestore. `HermesMockClient` / LLM la leen. |
| **La Siguiente Pregunta (Objetivo)** | `DiagnosticEngine` | El LLM o `HermesMockClient` le dan redacción y tono, pero el motor define qué campo falta. |
| **El Readiness (`operational_readiness`)** | `DiagnosticEngine` | Indica si los datos son suficientes para ir a admisión o registrar la incidencia. |
| **El Escalado Humano** | `DiagnosticEngine` (vía `SecurityPolicy`) | Detiene la interacción automatizada y marca el caso para revisión. |
| **La Creación de Incidencia** | `DiagnosticEngine` | Si decide que la fase es `INTAKE` y el readiness es `True`, se procede a la creación del ticket. |

---

## Consecuencias

* **Mantenibilidad**: Para entender por qué Hermes realizó una pregunta concreta, basta con abrir el [diagnostic_engine.py](file:///Users/pedro/AgentePlagas%20/hermes-pest-control/backend/app/diagnostics/diagnostic_engine.py).
* **Consistencia**: Al eliminar la duplicación de código en la extracción y de palabras clave de seguridad, se previene cualquier discrepancia de comportamiento entre los entornos de test (mock runtime) y producción (LLM runtime).
* **Estabilidad**: La suite completa de 396 tests unitarios, 18 evaluaciones offline funcionales y 12 evaluaciones multiturn de comportamiento conversacional pasan al 100% de éxito de forma limpia.
