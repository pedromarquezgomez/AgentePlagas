#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${BACKEND_DIR}/.." && pwd)"
ENV_FILE="${BACKEND_DIR}/.env.llm.local"
AGENT_HEALTH_URL="${HERMES_AGENT_HEALTH_URL:-http://127.0.0.1:9100/health}"
BACKEND_BASE_URL="${BACKEND_BASE_URL:-http://127.0.0.1:8000}"
AGENT_LOG_FILE="${HERMES_AGENT_LOG_FILE:-/tmp/hermes-agent-llm-shadow-smoke.log}"
BACKEND_LOG_FILE="${HERMES_BACKEND_LOG_FILE:-/tmp/hermes-backend-shadow-smoke.log}"
AGENT_PID=""
BACKEND_PID=""

cleanup() {
  if [[ -n "${BACKEND_PID}" ]] && kill -0 "${BACKEND_PID}" 2>/dev/null; then
    kill "${BACKEND_PID}" 2>/dev/null || true
    wait "${BACKEND_PID}" 2>/dev/null || true
  fi
  if [[ -n "${AGENT_PID}" ]] && kill -0 "${AGENT_PID}" 2>/dev/null; then
    kill "${AGENT_PID}" 2>/dev/null || true
    wait "${AGENT_PID}" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}."
  echo "Create it locally with OPENAI_API_KEY, OPENAI_MODEL, and LLM settings."
  exit 1
fi

if curl -fsS "${AGENT_HEALTH_URL}" >/dev/null 2>&1; then
  echo "Hermes Agent already responds at ${AGENT_HEALTH_URL}."
  echo "Stop the existing agent before running this smoke test."
  exit 1
fi

if curl -fsS "${BACKEND_BASE_URL}/health" >/dev/null 2>&1; then
  echo "Backend already responds at ${BACKEND_BASE_URL}."
  echo "Stop the existing backend before running this smoke test."
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "OPENAI_API_KEY is not configured in ${ENV_FILE}."
  exit 1
fi

if [[ -z "${OPENAI_MODEL:-}" ]]; then
  echo "OPENAI_MODEL is not configured in ${ENV_FILE}."
  exit 1
fi

echo "Starting Hermes LLM Agent..."
(
  cd "${REPO_ROOT}"
  make hermes-agent-llm
) >"${AGENT_LOG_FILE}" 2>&1 &
AGENT_PID="$!"

echo "Waiting for Hermes LLM Agent..."
for _ in {1..60}; do
  if curl -fsS "${AGENT_HEALTH_URL}" >/dev/null 2>&1; then
    echo "Hermes LLM Agent is ready."
    break
  fi
  if ! kill -0 "${AGENT_PID}" 2>/dev/null; then
    echo "Hermes LLM Agent exited before becoming ready."
    echo "Agent log: ${AGENT_LOG_FILE}"
    tail -n 80 "${AGENT_LOG_FILE}" 2>/dev/null || true
    exit 1
  fi
  sleep 1
done

if ! curl -fsS "${AGENT_HEALTH_URL}" >/dev/null 2>&1; then
  echo "Timed out waiting for Hermes LLM Agent."
  echo "Agent log: ${AGENT_LOG_FILE}"
  tail -n 80 "${AGENT_LOG_FILE}" 2>/dev/null || true
  exit 1
fi

echo "Starting backend with Hermes shadow mode enabled..."
(
  cd "${BACKEND_DIR}"
  APP_ENV=development \
  AUTH_MODE=disabled \
  HERMES_MODE=mock \
  HERMES_SHADOW_MODE=true \
  HERMES_SHADOW_API_URL=http://127.0.0.1:9100/agent \
  HERMES_SHADOW_SAMPLE_RATE=1.0 \
  HERMES_SHADOW_TIMEOUT_SECONDS=20 \
  .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
) >"${BACKEND_LOG_FILE}" 2>&1 &
BACKEND_PID="$!"

echo "Waiting for backend..."
for _ in {1..60}; do
  if curl -fsS "${BACKEND_BASE_URL}/health" >/dev/null 2>&1; then
    echo "Backend is ready."
    break
  fi
  if ! kill -0 "${BACKEND_PID}" 2>/dev/null; then
    echo "Backend exited before becoming ready."
    echo "Backend log: ${BACKEND_LOG_FILE}"
    tail -n 80 "${BACKEND_LOG_FILE}" 2>/dev/null || true
    exit 1
  fi
  sleep 1
done

if ! curl -fsS "${BACKEND_BASE_URL}/health" >/dev/null 2>&1; then
  echo "Timed out waiting for backend."
  echo "Backend log: ${BACKEND_LOG_FILE}"
  tail -n 80 "${BACKEND_LOG_FILE}" 2>/dev/null || true
  exit 1
fi

SMOKE_USER_ID="shadow-smoke-$(date +%s)"
CONVERSATION_ID="telegram:${SMOKE_USER_ID}"
MESSAGE_PAYLOAD="$(mktemp)"
RESPONSE_FILE="$(mktemp)"
SHADOW_FILE="$(mktemp)"

cat >"${MESSAGE_PAYLOAD}" <<JSON
{
  "channel": "telegram",
  "external_user_id": "${SMOKE_USER_ID}",
  "external_chat_id": "shadow-smoke-chat",
  "message_type": "text",
  "text": "Tengo cucarachas en la cocina en Torremolinos desde hace una semana",
  "attachments": [],
  "metadata": {}
}
JSON

echo "Posting /messages/test..."
curl -fsS \
  -X POST "${BACKEND_BASE_URL}/messages/test" \
  -H "Content-Type: application/json" \
  --data @"${MESSAGE_PAYLOAD}" \
  >"${RESPONSE_FILE}"

"${BACKEND_DIR}/.venv/bin/python" - "${RESPONSE_FILE}" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    data = json.load(handle)

action_type = data.get("action", {}).get("type")
if action_type != "create_incident":
    raise SystemExit(f"Expected primary action create_incident, got {action_type!r}")
PY

echo "Checking /audit/shadow-decisions..."
curl -fsS \
  "${BACKEND_BASE_URL}/audit/shadow-decisions?conversation_id=${CONVERSATION_ID}&limit=5" \
  >"${SHADOW_FILE}"

"${BACKEND_DIR}/.venv/bin/python" - "${SHADOW_FILE}" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    records = json.load(handle)

if not records:
    raise SystemExit("Expected at least one ShadowDecisionRecord, got none.")

record = records[0]
required = [
    "trace_id",
    "conversation_id",
    "primary_action_type",
    "shadow_action_type",
    "agreement_summary",
]
missing = [field for field in required if field not in record]
if missing:
    raise SystemExit(f"ShadowDecisionRecord missing fields: {missing}")

print("Shadow smoke OK")
print(f"conversation_id={record['conversation_id']}")
print(f"primary_action_type={record['primary_action_type']}")
print(f"shadow_action_type={record['shadow_action_type']}")
print(f"agreement_summary={record['agreement_summary']}")
PY

echo "Stopping local services..."
echo "Agent log: ${AGENT_LOG_FILE}"
echo "Backend log: ${BACKEND_LOG_FILE}"
