from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    telegram_bot_token: str = ""
    firebase_project_id: str = ""
    firebase_credentials_path: str = ""
    hermes_api_url: str = ""
    hermes_api_key: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

