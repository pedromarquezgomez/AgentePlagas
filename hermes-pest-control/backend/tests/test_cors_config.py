import pytest

from app.config.cors import CorsConfigurationError, get_cors_allowed_origins
from app.config.settings import Settings


def test_cors_uses_local_defaults_in_development() -> None:
    settings = Settings(app_env="development")

    origins = get_cors_allowed_origins(settings)

    assert origins == ["http://127.0.0.1:5173", "http://localhost:5173"]


def test_cors_uses_configured_origins_and_frontend_url() -> None:
    settings = Settings(
        app_env="production",
        cors_allowed_origins="https://panel.example.com, https://admin.example.com/",
        frontend_public_url="https://panel.example.com/",
    )

    origins = get_cors_allowed_origins(settings)

    assert origins == ["https://panel.example.com", "https://admin.example.com"]


def test_cors_rejects_wildcard_in_production() -> None:
    settings = Settings(app_env="production", cors_allowed_origins="*")

    with pytest.raises(CorsConfigurationError):
        get_cors_allowed_origins(settings)
