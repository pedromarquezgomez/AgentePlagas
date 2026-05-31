from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config.settings import Settings
from app.services.firestore_factory import FirestoreConfigurationError, get_firestore_service
from app.services.firestore_service import FirestoreService
from app.services.mock_firestore_service import MockFirestoreService


async def main() -> int:
    settings = Settings()
    try:
        service = get_firestore_service(settings)
    except FirestoreConfigurationError as exc:
        print("Firestore check")
        print(f"app_env={settings.app_env}")
        print("result=failed")
        print(f"reason={exc}")
        return 1

    mode = _service_mode(service)

    print("Firestore check")
    print(f"app_env={settings.app_env}")
    print(f"firestore_mode={mode}")
    print(f"firebase_project_id_configured={bool(settings.firebase_project_id)}")
    print(
        "firebase_credentials_configured="
        f"{bool(settings.firebase_credentials_path or settings.firebase_credentials_json)}"
    )
    print(f"firestore_emulator_enabled={settings.use_firestore_emulator}")

    document_id = f"check-{uuid4()}"
    payload = {
        "status": "started",
        "mode": mode,
        "ok": True,
        "tags": ["firestore", "system_check"],
        "metadata": {
            "app_env": settings.app_env,
            "project_id_configured": bool(settings.firebase_project_id),
        },
        "checked_at": datetime.now(timezone.utc),
    }

    created = await service.create_document(
        "system_checks",
        payload,
        document_id=document_id,
    )
    read_after_create = await service.get_document("system_checks", created["id"])
    await service.update_document(
        "system_checks",
        created["id"],
        {
            "status": "completed",
            "completed": True,
            "completed_at": datetime.now(timezone.utc),
        },
    )
    read_after_update = await service.get_document("system_checks", created["id"])

    if read_after_create is None or read_after_update is None:
        print("result=failed")
        print("reason=system check document could not be read")
        return 1

    if read_after_update.get("status") != "completed":
        print("result=failed")
        print("reason=system check document was not updated")
        return 1

    print("result=ok")
    print(f"collection=system_checks")
    print(f"document_id={created['id']}")
    return 0


def _service_mode(service: FirestoreService | MockFirestoreService) -> str:
    if isinstance(service, MockFirestoreService):
        return "mock"
    return "real"


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
