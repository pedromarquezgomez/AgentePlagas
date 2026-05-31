from fastapi import APIRouter

from app.config.settings import settings
from app.services.firestore_factory import has_firestore_real_config

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def readiness_check() -> dict[str, object]:
    checks = {
        "app_env": settings.app_env,
        "firestore_mode": _firestore_mode(),
        "auth_mode": settings.auth_mode,
        "auth_ready": _auth_ready(),
        "firestore_ready": _firestore_ready(),
    }
    degraded_reasons = _degraded_reasons(checks)

    return {
        "status": "ready" if not degraded_reasons else "degraded",
        "checks": checks,
        "degraded_reasons": degraded_reasons,
    }


def _firestore_mode() -> str:
    if settings.app_env == "test":
        return "mock"
    if has_firestore_real_config(settings):
        return "real"
    if settings.app_env == "development":
        return "mock"
    return "unconfigured"


def _firestore_ready() -> bool:
    if settings.app_env == "production":
        return has_firestore_real_config(settings)
    return True


def _auth_ready() -> bool:
    auth_mode = settings.auth_mode.lower()
    if settings.app_env == "production" and auth_mode == "disabled":
        return False
    if auth_mode == "api_key":
        if settings.app_env == "production":
            return bool(settings.admin_api_key)
        return bool(settings.admin_api_key) if settings.require_admin_auth else True
    if auth_mode == "firebase":
        return settings.firebase_auth_enabled and bool(settings.firebase_project_id)
    return auth_mode == "disabled"


def _degraded_reasons(checks: dict[str, object]) -> list[str]:
    reasons: list[str] = []
    if checks["app_env"] == "production" and checks["auth_mode"] == "disabled":
        reasons.append("AUTH_MODE=disabled is not allowed in production.")
    if not checks["auth_ready"]:
        reasons.append("Authentication is not ready.")
    if not checks["firestore_ready"]:
        reasons.append("Firestore real configuration is required in production.")
    return reasons
