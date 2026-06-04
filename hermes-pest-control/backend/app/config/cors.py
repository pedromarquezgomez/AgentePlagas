from app.config.settings import Settings

LOCAL_DEV_ORIGINS = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:5174",
    "http://localhost:5174",
    "http://127.0.0.1:5175",
    "http://localhost:5175",
    "http://127.0.0.1:5176",
    "http://localhost:5176",
    "http://127.0.0.1:5177",
    "http://localhost:5177",
]


class CorsConfigurationError(RuntimeError):
    pass


def get_cors_allowed_origins(settings: Settings) -> list[str]:
    configured_origins = _split_origins(settings.cors_allowed_origins)
    if settings.frontend_public_url:
        configured_origins.append(settings.frontend_public_url.rstrip("/"))

    origins = configured_origins or ([] if settings.app_env == "production" else LOCAL_DEV_ORIGINS)
    if settings.app_env == "production" and "*" in origins:
        raise CorsConfigurationError("Wildcard CORS origin is not allowed in production.")

    return _dedupe(origins)


def _split_origins(raw_value: str) -> list[str]:
    return [
        origin.strip().rstrip("/")
        for origin in raw_value.split(",")
        if origin.strip()
    ]


def _dedupe(origins: list[str]) -> list[str]:
    deduped: list[str] = []
    for origin in origins:
        if origin not in deduped:
            deduped.append(origin)
    return deduped
