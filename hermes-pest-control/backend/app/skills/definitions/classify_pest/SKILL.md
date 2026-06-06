---
name: classify_pest
description: Identify the pest type from the customer message.
allowed_outputs:
  - pest_type
  - confidence
  - missing_fields
forbidden_effects:
  - database_write
  - channel_send
  - tool_execution
risk_level: low
requires_backend_service: true
---
Identifica el tipo de plaga a partir del mensaje del cliente.

Clasifica la plaga en uno de estos tres grupos:
1. DISCOVERY: cucarachas (cockroach), roedores (rodent), hormigas (ant), avispas (wasp), termitas (termite).
2. DIAGNOSIS: plagas ambiguas o desconocidas (ej. plantas, limoneros, bichos verdes).
3. INTAKE DIRECTO: chinches (bedbugs), avispero visible, retirada de enjambre, rata muerta.

Normaliza los términos al inglés según el contrato:
- cucarachas -> cockroach
- roedores/ratas/ratones -> rodent
- hormigas -> ant
- avispas/avispero -> wasp
- termitas -> termite
Si es incierto, clasifícalo como unknown.
