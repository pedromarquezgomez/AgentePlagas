#!/usr/bin/env bash
# smoke_test_llm.sh — Verifica AGENT_PROVIDER=llm en local (Sprint 16)
#
# USO:
#   # Terminal 1: arrancar el backend con credenciales LLM cargadas
#   set -a; source backend/.env.llm.local; set +a
#   make dev
#
#   # Terminal 2: ejecutar este script
#   bash backend/scripts/smoke_test_llm.sh
#
# El script NO lanza el servidor. Asume que ya está corriendo en :8000.
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
PASS=0
FAIL=0

green()  { echo -e "\033[0;32m✓ $*\033[0m"; }
red()    { echo -e "\033[0;31m✗ $*\033[0m"; }
yellow() { echo -e "\033[0;33m➜ $*\033[0m"; }

check() {
    local label="$1"
    local result="$2"
    if [[ "$result" == "true" ]]; then
        green "$label"
        ((PASS++)) || true
    else
        red "$label"
        ((FAIL++)) || true
    fi
}

# ---------------------------------------------------------------------------
yellow "Verificando que el servidor está activo..."
curl -fsS "${BASE_URL}/health" > /dev/null || {
    red "El servidor no responde en ${BASE_URL}. Arranca el backend primero."
    exit 1
}
green "Servidor activo en ${BASE_URL}"

# ---------------------------------------------------------------------------
yellow ""
yellow "=== Test 1: Conversación completa — cucarachas en restaurante ==="

RESPONSE=$(curl -fsS -X POST "${BASE_URL}/messages/test" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "telegram",
    "external_user_id": "smoke-llm-user",
    "external_chat_id": "smoke-llm-chat",
    "message_type": "text",
    "text": "Tengo cucarachas en la cocina de mi restaurante. Mi nombre es Pedro.",
    "attachments": [],
    "metadata": {}
  }')

echo ""
echo "Respuesta:"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

# Garantía 1: El LLM responde (reply no vacío)
REPLY=$(echo "$RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('reply','')) > 0)" 2>/dev/null || echo "false")
check "Garantía 1 — LLM devuelve reply no vacío" "$REPLY"

# Garantía 2: No ejecuta tools directamente (solo propone)
ACTION=$(echo "$RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('action',{}).get('type','') in ['create_incident','collect_missing_data','escalate_to_human','reply_only'])" 2>/dev/null || echo "false")
check "Garantía 2 — action.type es una propuesta válida (no ejecución)" "$ACTION"

# Garantía 3: No hay tool_executed en metadata
NO_EXEC=$(echo "$RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print('tool_executed' not in d.get('metadata',{}))" 2>/dev/null || echo "false")
check "Garantía 3 — metadata no contiene tool_executed (no ejecución directa)" "$NO_EXEC"

# ---------------------------------------------------------------------------
yellow ""
yellow "=== Test 2: Verificar /config/status reporta agent_provider=llm ==="

CONFIG=$(curl -fsS "${BASE_URL}/config/status")
PROVIDER=$(echo "$CONFIG" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('agent_provider','') == 'llm' or d.get('hermes_mode','') == 'llm')" 2>/dev/null || echo "false")
check "Garantía 4 — /config/status reporta agent_provider=llm" "$PROVIDER"
echo "Config: $(echo "$CONFIG" | python3 -m json.tool 2>/dev/null | head -20 || echo "$CONFIG")"

# ---------------------------------------------------------------------------
yellow ""
yellow "=== Test 3: Mensaje incompleto → collect_missing_data ==="

PARTIAL=$(curl -fsS -X POST "${BASE_URL}/messages/test" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "telegram",
    "external_user_id": "smoke-llm-user-2",
    "external_chat_id": "smoke-llm-chat-2",
    "message_type": "text",
    "text": "Hola, buenas tardes.",
    "attachments": [],
    "metadata": {}
  }')

PARTIAL_ACTION=$(echo "$PARTIAL" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('action',{}).get('type',''))" 2>/dev/null || echo "")
PARTIAL_VALID=$(echo "$PARTIAL" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('action',{}).get('type','') in ['reply_only','collect_missing_data'])" 2>/dev/null || echo "false")
check "Garantía 5 — Mensaje incompleto → reply_only o collect_missing_data" "$PARTIAL_VALID"

# ---------------------------------------------------------------------------
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Resultados: ${PASS} pasaron, ${FAIL} fallaron"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [[ "$FAIL" -gt 0 ]]; then
    exit 1
fi
