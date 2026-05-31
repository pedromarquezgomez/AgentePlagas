from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    cors_allowed_origins: str = ""
    frontend_public_url: str = ""
    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""
    telegram_webhook_url: str = ""
    telegram_internal_alert_chat_id: str = ""
    firebase_project_id: str = ""
    firebase_credentials_path: str = ""
    firebase_credentials_json: str = ""
    use_firestore_emulator: bool = False
    firestore_emulator_host: str = ""
    hermes_mode: str = "mock"
    hermes_api_url: str = ""
    hermes_api_key: str = ""
    hermes_timeout_seconds: float = 30.0
    hermes_agent_server_port: int = 9100
    hermes_skills_dir: str = "../hermes/skills"
    hermes_agent_mode: str = "local"
    admin_api_key: str = ""
    require_admin_auth: bool = False
    auth_mode: str = "api_key"
    firebase_auth_enabled: bool = False
    google_calendar_enabled: bool = False
    google_calendar_id: str = ""
    google_calendar_credentials_path: str = ""
    google_calendar_credentials_json: str = ""
    whatsapp_enabled: bool = False
    whatsapp_provider: str = "meta"
    whatsapp_verify_token: str = ""
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_webhook_secret: str = ""
    whatsapp_graph_api_version: str = "v20.0"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
