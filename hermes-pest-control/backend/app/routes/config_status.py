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
        "cors_allowed_origins_configured": bool(settings.cors_allowed_origins),
        "frontend_public_url_configured": bool(settings.frontend_public_url),
        "hermes_mode": settings.hermes_mode,
        "hermes_api_url_configured": bool(settings.hermes_api_url),
        "hermes_api_key_configured": bool(settings.hermes_api_key),
        "hermes_agent_mode": settings.hermes_agent_mode,
        "hermes_skills_dir_configured": bool(settings.hermes_skills_dir),
        "llm_provider": settings.llm_provider,
        "openai_api_key_configured": bool(settings.openai_api_key),
        "openai_model_configured": bool(settings.openai_model),
        "agent_max_output_tokens_configured": bool(settings.agent_max_output_tokens),
        "telegram_configured": bool(settings.telegram_bot_token),
        "firestore_mode": _firestore_mode(),
        "firebase_project_id_configured": bool(settings.firebase_project_id),
        "firebase_credentials_configured": has_firestore_credentials(settings),
        "firestore_emulator_enabled": settings.use_firestore_emulator,
        "auth_mode": settings.auth_mode,
        "firebase_auth_enabled": settings.firebase_auth_enabled,
        "admin_auth_required": settings.require_admin_auth,
        "admin_api_key_configured": bool(settings.admin_api_key),
        "google_calendar_enabled": settings.google_calendar_enabled,
        "google_calendar_id_configured": bool(settings.google_calendar_id),
        "google_calendar_credentials_configured": bool(
            settings.google_calendar_credentials_path
            or settings.google_calendar_credentials_json
        ),
        "whatsapp_enabled": settings.whatsapp_enabled,
        "whatsapp_provider": settings.whatsapp_provider,
        "whatsapp_access_token_configured": bool(settings.whatsapp_access_token),
        "whatsapp_phone_number_id_configured": bool(settings.whatsapp_phone_number_id),
        "whatsapp_verify_token_configured": bool(settings.whatsapp_verify_token),
    }


def _firestore_mode() -> str:
    if settings.app_env == "test":
        return "mock"

    if has_firestore_real_config(settings):
        return "real"

    if settings.app_env == "development":
        return "mock"

    return "real"
