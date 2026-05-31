from fastapi import APIRouter

from app.config.settings import settings
from app.services.firestore_factory import (
    has_firestore_credentials,
    has_firestore_real_config,
)

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/status")
async def config_status() -> dict[str, bool | str]:
    return {
        "app_env": settings.app_env,
        "hermes_mode": settings.hermes_mode,
        "hermes_api_url_configured": bool(settings.hermes_api_url),
        "hermes_api_key_configured": bool(settings.hermes_api_key),
        "hermes_agent_mode": settings.hermes_agent_mode,
        "hermes_skills_dir_configured": bool(settings.hermes_skills_dir),
        "telegram_configured": bool(settings.telegram_bot_token),
        "firestore_mode": _firestore_mode(),
        "firebase_project_id_configured": bool(settings.firebase_project_id),
        "firebase_credentials_configured": has_firestore_credentials(settings),
        "firestore_emulator_enabled": settings.use_firestore_emulator,
        "admin_auth_required": settings.require_admin_auth,
        "admin_api_key_configured": bool(settings.admin_api_key),
    }


def _firestore_mode() -> str:
    if settings.app_env == "test":
        return "mock"

    if has_firestore_real_config(settings):
        return "real"

    if settings.app_env == "development":
        return "mock"

    return "real"
