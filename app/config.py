"""
Application Configuration Module

Uses Pydantic BaseSettings to load environment variables from the .env file
with type validation and default fallback values.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application Settings schema matching system environment variables.
    """

    PROJECT_NAME: str = "Blood Relay API"
    VERSION: str = "0.1.0"
    DEBUG: bool = True

    # Database Configuration
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "blood_relay_db"

    # Default PostgreSQL SQLAlchemy URL
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/blood_relay_db"

    # JWT Authentication configuration (for future step implementation)
    SECRET_KEY: str = "supersecretkey_change_me_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


# Global settings instance
settings = Settings()
