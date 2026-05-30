from fastapi import APIRouter

from app.config.settings import settings

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/status")
async def config_status() -> dict[str, bool | str]:
    return {
        "app_env": settings.app_env,
        "hermes_mode": settings.hermes_mode,
        "telegram_configured": bool(settings.telegram_bot_token),
        "firestore_mode": _firestore_mode(),
        "firebase_project_id_configured": bool(settings.firebase_project_id),
    }


def _firestore_mode() -> str:
    if settings.app_env == "test":
        return "mock"

    has_real_firestore_config = any(
        [
            settings.use_firestore_emulator,
            settings.firebase_credentials_path,
            settings.firebase_credentials_json,
        ]
    )
    if has_real_firestore_config:
        return "real"

    if settings.app_env == "development":
        return "mock"

    return "real"
