---
name: escalate_to_human
description: Escalate sensitive, unsafe, legal, pricing, or unclear cases.
allowed_outputs:
  - action.escalate_to_human
  - incident
  - reply
forbidden_effects:
  - medical_advice
  - chemical_instructions
  - channel_send
risk_level: high
requires_backend_service: true
---
Deriva la conversación al operador humano en cualquiera de los siguientes casos:
- Exposición a químicos o plaguicidas.
- Presencia de personas vulnerables (niños, ancianos, hospitales).
- Presencia de mascotas afectadas.
- Locales comerciales que presenten riesgo de seguridad alimentaria grave.
- Amenazas legales o demandas de garantías exactas.
- Precios o presupuestos detallados que requieran cálculo comercial específico.
- Instrucciones directas de tratamiento o eliminación peligrosas que pongan en riesgo al cliente.
