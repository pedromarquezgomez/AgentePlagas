# Política de Admisión de Incidencias (Intake Policy)

La fase de admisión (INTAKE) tiene como único objetivo recolectar los datos administrativos mínimos necesarios para abrir una incidencia válida en el sistema una vez que el problema técnico ha sido comprendido.

## Datos Mínimos de Admisión

Para registrar una incidencia en el sistema se requiere:
1.  **Tipo de plaga** (pest_type): Identificado o diagnosticado previamente.
2.  **Ubicación/Localización** (location): Dirección física o localidad del suceso.
3.  **Nombre del contacto** (customer_name): Persona de contacto.
4.  **Zona afectada** (affected_area): Heredada de la fase de descubrimiento.

## Reglas de Ejecución del Intake

1.  **Nunca Intake-First**:
    *   Queda estrictamente prohibido solicitar datos de contacto, dirección, localidad o teléfono en los primeros turnos de la conversación ante plagas del grupo DISCOVERY o DIAGNOSIS, a menos que sea una urgencia crítica de salud.
    *   La transición a INTAKE solo ocurre cuando se ha completado la fase DISCOVERY (recolectadas las 4 variables de descubrimiento) o se ha resuelto el diagnóstico en DIAGNOSIS.

2.  **Aprovechamiento del Contexto Histórico (CRM)**:
    *   Revisa `customer_context` en `business_context` antes de pedir cualquier dato administrativo.
    *   Si el nombre del cliente (`customer_name`) o la ubicación habitual (`last_location`) ya constan en el historial de Firestore, **NO** los vuelvas a preguntar de cero.
    *   Si los datos existen, utilízalos implícitamente o confírmalos sutilmente (ej: "¿Registramos el aviso a tu nombre, Pedro?", o "¿Es para la calle Larios, 5, donde estuvimos la última vez?").
    *   Si el cliente tiene múltiples locales (`has_multiple_sites`), pregúntale cuál de sus locales conocidos es el afectado antes de pedir una dirección nueva de forma genérica.

3.  **Heredar Datos Técnicos**:
    *   Al transicionar de DISCOVERY o DIAGNOSIS a INTAKE, asegúrate de heredar y arrastrar toda la información técnica extraída (`environment_type`, `affected_zone`, `severity`, `first_seen`) para inyectarla en la incidencia propuesta. No vuelvas a preguntar por la zona afectada ni el tipo de plaga en INTAKE.
