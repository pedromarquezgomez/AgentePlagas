from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config.settings import Settings
from app.services.gmail_tool_executor import (
    GmailToolDisabledError,
    GmailToolExecutionError,
    GmailToolExecutor,
    GmailToolPayloadError,
)


async def main() -> int:
    settings = Settings()
    executor = GmailToolExecutor(settings=settings)

    print("Gmail draft check")
    print(f"app_env={settings.app_env}")
    print(f"gmail_tools_enabled={settings.gmail_tools_enabled}")
    print(f"gmail_draft_execution_enabled={settings.gmail_draft_execution_enabled}")
    print(
        "gmail_credentials_configured="
        f"{bool(settings.gmail_credentials_path or settings.gmail_credentials_json)}"
    )
    print(f"gmail_delegated_user_configured={bool(settings.gmail_delegated_user)}")

    try:
        profile = await executor.check_connection()
    except (GmailToolDisabledError, GmailToolExecutionError) as exc:
        print("auth_check=failed")
        print(f"reason={exc}")
        return 1

    print("auth_check=ok")
    print(f"email_configured={profile['email_configured']}")
    print(f"messages_total={profile.get('messages_total')}")
    print(f"threads_total={profile.get('threads_total')}")

    if os.environ.get("CONFIRM_CREATE_GMAIL_DRAFT") != "true":
        print("draft_create=skipped")
        print("Set CONFIRM_CREATE_GMAIL_DRAFT=true to create a test draft.")
        return 0

    payload = {
        "recipient": os.environ.get("GMAIL_TEST_DRAFT_RECIPIENT", "cliente@example.test"),
        "subject": os.environ.get(
            "GMAIL_TEST_DRAFT_SUBJECT",
            "Hermes Gmail draft check",
        ),
        "body": os.environ.get(
            "GMAIL_TEST_DRAFT_BODY",
            (
                "Borrador de prueba creado por Hermes Pest Control. "
                f"No enviar. Fecha UTC: {datetime.now(timezone.utc).isoformat()}"
            ),
        ),
    }

    try:
        result = await executor.create_draft(payload)
    except GmailToolPayloadError as exc:
        print("draft_create=failed")
        print(f"reason={exc}")
        return 1
    except (GmailToolDisabledError, GmailToolExecutionError) as exc:
        print("draft_create=failed")
        print(f"reason={exc}")
        return 1

    print("draft_create=ok")
    print(f"provider={result.get('provider')}")
    print(f"draft_id={result.get('draft_id')}")
    print(f"message_id={result.get('message_id')}")
    print("email_sent=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
