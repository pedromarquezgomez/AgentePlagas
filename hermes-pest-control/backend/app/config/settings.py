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
    agent_provider: str = ""
    hermes_mode: str = "mock"
    hermes_api_url: str = ""
    hermes_api_key: str = ""
    hermes_timeout_seconds: float = 30.0
    hermes_shadow_mode: bool = False
    hermes_shadow_api_url: str = ""
    hermes_shadow_api_key: str = ""
    hermes_shadow_sample_rate: float = 1.0
    hermes_shadow_timeout_seconds: float = 20.0
    hermes_pilot_mode: bool = False
    hermes_pilot_sample_rate: float = 1.0
    hermes_pilot_allowed_channels: str = "telegram"
    hermes_pilot_require_gate: bool = True
    hermes_pilot_max_response_length: int = 800
    hermes_agent_server_port: int = 9100
    hermes_skills_dir: str = "../hermes/skills"
    hermes_agent_mode: str = "local"
    hermes_agent_api_key: str = ""
    llm_provider: str = "openai"
    llm_api_key: str = ""
    llm_model: str = ""
    llm_timeout_seconds: float = 20.0
    llm_fallback_provider: str = "mock"
    llm_active_mode: str = "pilot"
    openai_api_key: str = ""
    openai_model: str = ""
    openai_timeout_seconds: float = 30.0
    agent_max_output_tokens: int = 1200
    agent_temperature: float = 0.0
    admin_api_key: str = ""
    require_admin_auth: bool = False
    auth_mode: str = "api_key"
    firebase_auth_enabled: bool = False
    google_calendar_enabled: bool = False
    google_calendar_id: str = ""
    google_calendar_credentials_path: str = ""
    google_calendar_credentials_json: str = ""
    gmail_tools_enabled: bool = False
    gmail_draft_execution_enabled: bool = False
    gmail_credentials_path: str = ""
    gmail_credentials_json: str = ""
    gmail_delegated_user: str = ""
    whatsapp_enabled: bool = False
    whatsapp_provider: str = "meta"
    whatsapp_verify_token: str = ""
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_webhook_secret: str = ""
    whatsapp_graph_api_version: str = "v20.0"
    synthetic_generation_mode: str = "template"
    synthetic_case_count: int = 50
    synthetic_output_path: str = "evals/synthetic/generated_cases.json"
    nous_hermes_enabled: bool = False
    nous_hermes_mode: str = "disabled"
    nous_hermes_tools_enabled: bool = False
    nous_hermes_allowed_tools: str = ""
    tool_harness_enforcement: str = "strict"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
