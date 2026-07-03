"""Centralised typed application configuration."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, PostgresDsn, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "staging", "production"]

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Known-insecure development defaults. If any of these survive into a
# production process it is a misconfiguration that must fail fast at
# startup rather than surface as a runtime 401/insecure credential.
INSECURE_OPENAI_KEY = "mock-key-for-development"
INSECURE_POSTGRES_PASSWORD = "docsmind"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    APP_NAME: str = "DocsMind"
    ENVIRONMENT: Environment = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    BACKEND_CORS_ORIGINS: list[str] = Field(default_factory=list)
    FRONTEND_URL: str = "http://localhost:5173"

    SECRET_KEY: str = Field(min_length=32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ALGORITHM: str = "HS256"
    EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS: int = 24

    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "docsmind"
    POSTGRES_PASSWORD: str = "docsmind"
    POSTGRES_DB: str = "docsmind"

    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_MAX_CONNECTIONS: int = 50

    RATE_LIMIT_PER_MINUTE: int = 120

    OPENAI_API_KEY: str = "mock-key-for-development"
    LLM_BASE_URL: str | None = None
    LLM_MODEL: str = "gpt-4o-mini"
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str | None = None
    QDRANT_STORAGE_PATH: str = "storage/qdrant"
    EMBEDDING_PROVIDER: str = "openai"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    RERANK_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    STORAGE_PROVIDER: str = "local"
    S3_BUCKET_NAME: str = "docsmind"
    S3_REGION: str = "us-east-1"
    S3_ACCESS_KEY_ID: str | None = None
    S3_SECRET_ACCESS_KEY: str | None = None
    S3_ENDPOINT_URL: str | None = None

    OCR_MIN_CHARS_THRESHOLD: int = 300
    OCR_ENABLE_PREPROCESSING: bool = True
    OCR_SCALE_FACTOR: int = 2

    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15

    # ---- SMTP / Email ----
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "DocsMind"
    SMTP_TLS: bool = True
    EMAILS_ENABLED: bool = True

    # ---- Google OAuth ----
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8006/api/v1/auth/google/callback"

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def _split_cors(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @computed_field
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @computed_field
    @property
    def google_oauth_enabled(self) -> bool:
        return bool(self.GOOGLE_CLIENT_ID and self.GOOGLE_CLIENT_SECRET)

    @computed_field
    @property
    def database_url(self) -> str:
        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=self.POSTGRES_USER,
                password=self.POSTGRES_PASSWORD,
                host=self.POSTGRES_HOST,
                port=self.POSTGRES_PORT,
                path=self.POSTGRES_DB,
            )
        )

    @computed_field
    @property
    def sync_database_url(self) -> str:
        return str(
            PostgresDsn.build(
                scheme="postgresql+psycopg",
                username=self.POSTGRES_USER,
                password=self.POSTGRES_PASSWORD,
                host=self.POSTGRES_HOST,
                port=self.POSTGRES_PORT,
                path=self.POSTGRES_DB,
            )
        )

    @computed_field
    @property
    def redis_url(self) -> str:
        return "redis://{0}:{1}/{2}".format(self.REDIS_HOST, self.REDIS_PORT, self.REDIS_DB)

    def production_safety_errors(self) -> list[str]:
        """Return misconfigurations that must block startup in production.

        Non-production environments are allowed to run with the convenient
        development defaults; production must supply real secrets. This turns
        a silent, deferred failure (e.g. every chat call 401ing because the
        OpenAI key is still the mock placeholder) into an immediate, loud
        boot failure.
        """
        if not self.is_production:
            return []

        errors: list[str] = []
        if self.EMBEDDING_PROVIDER == "openai" and (
            not self.OPENAI_API_KEY or self.OPENAI_API_KEY == INSECURE_OPENAI_KEY
        ):
            errors.append(
                "OPENAI_API_KEY is unset or still the development placeholder while "
                "EMBEDDING_PROVIDER=openai; chat and embeddings will fail at runtime."
            )
        if self.POSTGRES_PASSWORD == INSECURE_POSTGRES_PASSWORD:
            errors.append(
                "POSTGRES_PASSWORD is still the insecure default 'docsmind'; set a real password."
            )
        return errors


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()