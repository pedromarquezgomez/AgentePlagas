from secrets import compare_digest

from fastapi import Header, HTTPException, status

from app.config.settings import settings


async def require_admin_auth(
    x_admin_api_key: str | None = Header(default=None),
) -> None:
    if not settings.require_admin_auth:
        return

    if (
        not settings.admin_api_key
        or not x_admin_api_key
        or not compare_digest(x_admin_api_key, settings.admin_api_key)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin API key.",
        )
