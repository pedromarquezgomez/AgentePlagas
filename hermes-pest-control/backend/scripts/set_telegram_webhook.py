#!/usr/bin/env python3
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv


def main() -> int:
    backend_dir = Path(__file__).resolve().parents[1]
    load_dotenv(backend_dir / ".env")

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    webhook_url = os.getenv("TELEGRAM_WEBHOOK_URL", "").strip()
    webhook_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip()

    if not token:
        print("Missing TELEGRAM_BOT_TOKEN.", file=sys.stderr)
        return 1
    if not webhook_url:
        print("Missing TELEGRAM_WEBHOOK_URL.", file=sys.stderr)
        return 1

    payload = {"url": webhook_url}
    if webhook_secret:
        payload["secret_token"] = webhook_secret

    api_url = f"https://api.telegram.org/bot{token}/setWebhook"

    try:
        response = httpx.post(api_url, json=payload, timeout=10.0)
        data = response.json()
    except httpx.HTTPError as exc:
        print(f"Telegram setWebhook request failed: {exc}", file=sys.stderr)
        return 1
    except ValueError:
        print("Telegram setWebhook returned invalid JSON.", file=sys.stderr)
        return 1

    if response.status_code >= 400 or data.get("ok") is not True:
        description = data.get("description", "unknown Telegram API error")
        print(f"Telegram setWebhook failed: {description}", file=sys.stderr)
        return 1

    print("Telegram webhook configured successfully.")
    print(f"Webhook URL: {webhook_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
