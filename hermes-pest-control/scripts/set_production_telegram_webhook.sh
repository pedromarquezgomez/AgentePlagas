#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${TELEGRAM_BOT_TOKEN:-}" ]]; then
  echo "Missing required environment variable: TELEGRAM_BOT_TOKEN" >&2
  exit 1
fi

if [[ -z "${CLOUD_RUN_URL:-}" ]]; then
  echo "Missing required environment variable: CLOUD_RUN_URL" >&2
  exit 1
fi

WEBHOOK_URL="${CLOUD_RUN_URL%/}/webhooks/telegram"

echo "About to configure Telegram production webhook:"
echo "${WEBHOOK_URL}"
echo "The bot token will not be printed."

read -r -p "Continue? Type 'set-webhook' to proceed: " confirmation
if [[ "${confirmation}" != "set-webhook" ]]; then
  echo "Aborted."
  exit 1
fi

if [[ -n "${TELEGRAM_WEBHOOK_SECRET:-}" ]]; then
  curl -fsS -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
    -H "Content-Type: application/json" \
    -d "{\"url\":\"${WEBHOOK_URL}\",\"secret_token\":\"${TELEGRAM_WEBHOOK_SECRET}\"}"
else
  curl -fsS "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook?url=${WEBHOOK_URL}"
fi
