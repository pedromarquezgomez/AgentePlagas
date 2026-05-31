#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

curl -sS -X POST "$BASE_URL/webhooks/whatsapp" \
  -H "Content-Type: application/json" \
  -d '{
    "object": "whatsapp_business_account",
    "entry": [
      {
        "id": "waba-smoke",
        "changes": [
          {
            "field": "messages",
            "value": {
              "messaging_product": "whatsapp",
              "metadata": {
                "display_phone_number": "34999000111",
                "phone_number_id": "phone-number-id"
              },
              "contacts": [
                {
                  "profile": { "name": "Cliente Smoke" },
                  "wa_id": "34600000000"
                }
              ],
              "messages": [
                {
                  "from": "34600000000",
                  "id": "wamid.smoke",
                  "timestamp": "1710000000",
                  "type": "text",
                  "text": {
                    "body": "Tengo cucarachas en la cocina en Torremolinos desde hace una semana"
                  }
                }
              ]
            }
          }
        ]
      }
    ]
  }'
echo
