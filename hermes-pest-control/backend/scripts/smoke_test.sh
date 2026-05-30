#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

echo "GET ${BASE_URL}/health"
curl -fsS "${BASE_URL}/health"
echo

echo "GET ${BASE_URL}/config/status"
curl -fsS "${BASE_URL}/config/status"
echo

echo "POST ${BASE_URL}/messages/test"
curl -fsS -X POST "${BASE_URL}/messages/test" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "telegram",
    "external_user_id": "smoke-user-1",
    "external_chat_id": "smoke-chat-1",
    "message_type": "text",
    "text": "Tengo cucarachas en la cocina en Torremolinos desde hace una semana",
    "attachments": [],
    "metadata": {}
  }'
echo
