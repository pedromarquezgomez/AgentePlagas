from __future__ import annotations

import json
from dataclasses import dataclass
from secrets import compare_digest
from typing import Any

from fastapi import Header, HTTPException, status

from app.config.settings import Settings, settings


@dataclass(frozen=True)
class AdminUserContext:
    auth_mode: str
    uid: str | None = None
    email: str | None = None
    name: str | None = None


class FirebaseAuthError(RuntimeError):
    pass


async def require_admin_user(
    authorization: str | None = Header(default=None),
    x_admin_api_key: str | None = Header(default=None),
) -> AdminUserContext:
    auth_mode = settings.auth_mode.lower()

    if auth_mode == "disabled":
        if settings.app_env == "production":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="AUTH_MODE=disabled is not allowed in production.",
            )
        return AdminUserContext(auth_mode="disabled")

    if auth_mode == "api_key":
        return _require_api_key(x_admin_api_key)

    if auth_mode == "firebase":
        return _require_firebase_user(authorization)

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Invalid AUTH_MODE configuration.",
    )


async def require_admin_auth(
    authorization: str | None = Header(default=None),
    x_admin_api_key: str | None = Header(default=None),
) -> AdminUserContext:
    return await require_admin_user(authorization, x_admin_api_key)


def _require_api_key(x_admin_api_key: str | None) -> AdminUserContext:
    if not settings.require_admin_auth:
        return AdminUserContext(auth_mode="api_key")

    if (
        not settings.admin_api_key
        or not x_admin_api_key
        or not compare_digest(x_admin_api_key, settings.admin_api_key)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin API key.",
        )

    return AdminUserContext(auth_mode="api_key", uid="admin-api-key")


def _require_firebase_user(authorization: str | None) -> AdminUserContext:
    if not settings.firebase_auth_enabled:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Firebase Auth is not enabled.",
        )

    token = _extract_bearer_token(authorization)
    try:
        decoded_token = verify_firebase_id_token(token, settings)
    except FirebaseAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Firebase authentication token.",
        ) from exc

    return AdminUserContext(
        auth_mode="firebase",
        uid=decoded_token.get("uid") or decoded_token.get("sub"),
        email=decoded_token.get("email"),
        name=decoded_token.get("name"),
    )


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Firebase authentication token.",
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Firebase authentication token.",
        )

    return token.strip()


def verify_firebase_id_token(token: str, current_settings: Settings = settings) -> dict[str, Any]:
    try:
        from firebase_admin import auth

        _ensure_firebase_admin_initialized(current_settings)
        return auth.verify_id_token(token)
    except Exception as exc:
        raise FirebaseAuthError("Firebase token verification failed.") from exc


def _ensure_firebase_admin_initialized(current_settings: Settings) -> None:
    import firebase_admin
    from firebase_admin import credentials

    if firebase_admin._apps:
        return

    options: dict[str, str] = {}
    if current_settings.firebase_project_id:
        options["projectId"] = current_settings.firebase_project_id

    if current_settings.firebase_credentials_path:
        credential = credentials.Certificate(current_settings.firebase_credentials_path)
        firebase_admin.initialize_app(credential, options=options or None)
        return

    if current_settings.firebase_credentials_json:
        credential_data = json.loads(current_settings.firebase_credentials_json)
        credential = credentials.Certificate(credential_data)
        firebase_admin.initialize_app(credential, options=options or None)
        return

    firebase_admin.initialize_app(options=options or None)
