#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${BACKEND_DIR}/.." && pwd)"
ENV_FILE="${BACKEND_DIR}/.env.llm.local"
HEALTH_URL="${HERMES_AGENT_HEALTH_URL:-http://127.0.0.1:9100/health}"
LOG_FILE="${HERMES_AGENT_LOG_FILE:-/tmp/hermes-agent-llm.log}"
AGENT_PID=""

cleanup() {
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

if curl -fsS "${HEALTH_URL}" >/dev/null 2>&1; then
  echo "Hermes Agent already responds at ${HEALTH_URL}."
  echo "Stop the existing agent before running this script so the eval uses a fresh local process."
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
) >"${LOG_FILE}" 2>&1 &
AGENT_PID="$!"

echo "Waiting for Hermes LLM Agent at ${HEALTH_URL}..."
for _ in {1..60}; do
  if curl -fsS "${HEALTH_URL}" >/dev/null 2>&1; then
    echo "Hermes LLM Agent is ready."
    break
  fi

  if ! kill -0 "${AGENT_PID}" 2>/dev/null; then
    echo "Hermes LLM Agent exited before becoming ready."
    echo "Agent log: ${LOG_FILE}"
    tail -n 80 "${LOG_FILE}" 2>/dev/null || true
    exit 1
  fi

  sleep 1
done

if ! curl -fsS "${HEALTH_URL}" >/dev/null 2>&1; then
  echo "Timed out waiting for Hermes LLM Agent."
  echo "Agent log: ${LOG_FILE}"
  tail -n 80 "${LOG_FILE}" 2>/dev/null || true
  exit 1
fi

set +e
(
  cd "${REPO_ROOT}"
  make evals-agent-llm
)
EVAL_EXIT_CODE="$?"
set -e

echo "Stopping Hermes LLM Agent..."
echo "Agent log: ${LOG_FILE}"
exit "${EVAL_EXIT_CODE}"
