#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv


def main() -> int:
    backend_dir = Path(__file__).resolve().parents[1]
    load_dotenv(backend_dir / ".env")

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print("Missing TELEGRAM_BOT_TOKEN.", file=sys.stderr)
        return 1

    api_url = f"https://api.telegram.org/bot{token}/getWebhookInfo"

    try:
        response = httpx.get(api_url, timeout=10.0)
        data = response.json()
    except httpx.HTTPError as exc:
        print(f"Telegram getWebhookInfo request failed: {exc}", file=sys.stderr)
        return 1
    except ValueError:
        print("Telegram getWebhookInfo returned invalid JSON.", file=sys.stderr)
        return 1

    print(json.dumps(data, indent=2, ensure_ascii=False))
    return 0 if response.status_code < 400 and data.get("ok") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
