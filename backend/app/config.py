from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = ""

    DATABASE_URL: str = "sqlite+aiosqlite:////data/db/tax_return.db"

    STORAGE_BACKEND: str = "local"
    STORAGE_PATH: str = "/data/documents"

    AI_PROVIDER: str = "claude"
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"
    AI_TIMEOUT_SECONDS: int = 15

    APP_PASSWORD_HASH: str = ""
    SESSION_MAX_AGE_DAYS: int = 1
    UNLOCK_SESSION_MINUTES: int = 30

    CORS_ORIGINS: str = "https://taxcc.signpega.com,http://127.0.0.1:3060"

    MAX_FILE_SIZE_MB: int = 20
    EXPORT_RETENTION_HOURS: int = 24
    EXPORT_PATH: str = "/data/exports"
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
