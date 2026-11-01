"""Centralised typed application configuration."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import AliasChoices, Field, PostgresDsn, computed_field, field_validator
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
    BACKEND_CORS_ORIGINS: Any = Field(default_factory=lambda: ["*"])
    FRONTEND_URL: str = "http://localhost:5173"

    SECRET_KEY: str = Field(min_length=32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ALGORITHM: str = "HS256"
    EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS: int = 24

    DATABASE_URL: str | None = None
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "docsmind"
    POSTGRES_PASSWORD: str = "docsmind"
    POSTGRES_DB: str = "docsmind"

    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10

    REDIS_URL: str | None = None
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_MAX_CONNECTIONS: int = 50

    RATE_LIMIT_PER_MINUTE: int = 120

    OPENAI_API_KEY: str = "mock-key-for-development"
    LLM_BASE_URL: str | None = None
    LLM_MODEL: str = "gpt-4o-mini"
    # LLM execution path. "openai" (real OpenAI, or any OpenAI-compatible server
    # when LLM_BASE_URL is set), "ollama" (local server, no key), or "local"
    # (in-process transformers, no key/network). See services/rag/llm_provider.py.
    LLM_PROVIDER: str = "openai"
    # Optional dedicated key for the LLM provider; falls back to OPENAI_API_KEY.
    LLM_API_KEY: str | None = None
    # Model used when LLM_PROVIDER=local (HuggingFace text-generation model id).
    LOCAL_LLM_MODEL: str = "Qwen/Qwen2.5-0.5B-Instruct"
    QDRANT_URL: str | None = None
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

    # Comma-separated emails that are granted admin on login (bootstraps the
    # first administrator; further admins are promoted from the admin panel).
    ADMIN_EMAILS: str = ""

    # ---- SMTP / Email ----
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = Field(default="", validation_alias=AliasChoices("SMTP_PASSWORD", "SMTP_PASS"))
    SMTP_FROM_EMAIL: str = Field(default="", validation_alias=AliasChoices("SMTP_FROM_EMAIL", "SMTP_FROM"))
    SMTP_FROM_NAME: str = "DocsMind"
    SMTP_TLS: bool = True
    EMAILS_ENABLED: bool = True
    # Google Apps Script Gmail relay (port 443, passwordless Gmail sending)
    GMAIL_RELAY_URL: str | None = None
    GMAIL_RELAY_SECRET: str | None = None
    EMAIL_WEBHOOK_URL: str | None = None

    # ---- Google OAuth ----
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8006/api/v1/auth/google/callback"

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def _split_cors(cls, value: Any) -> list[str]:
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("[") and value.endswith("]"):
                import json
                try:
                    parsed = json.loads(value)
                    if isinstance(parsed, list):
                        return [str(o).strip() for o in parsed if str(o).strip()]
                except Exception:
                    pass
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        if isinstance(value, list):
            return [str(o).strip() for o in value if str(o).strip()]
        return ["*"]

    @field_validator("SMTP_FROM_EMAIL", mode="before")
    @classmethod
    def _clean_from_email(cls, value: str) -> str:
        if isinstance(value, str) and "<" in value and ">" in value:
            import email.utils
            _, addr = email.utils.parseaddr(value)
            return addr or value
        return value

    @computed_field
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @computed_field
    @property
    def google_oauth_enabled(self) -> bool:
        return bool(self.GOOGLE_CLIENT_ID and self.GOOGLE_CLIENT_SECRET)

    @property
    def admin_emails(self) -> set[str]:
        """Lowercased set of bootstrap admin emails from ADMIN_EMAILS."""
        return {e.strip().lower() for e in self.ADMIN_EMAILS.split(",") if e.strip()}

    @computed_field
    @property
    def database_url(self) -> str:
        if self.DATABASE_URL:
            import urllib.parse
            parsed = urllib.parse.urlsplit(self.DATABASE_URL)
            q_dict = urllib.parse.parse_qs(parsed.query)
            q_dict.pop("channel_binding", None)
            if "sslmode" in q_dict:
                q_dict["ssl"] = q_dict.pop("sslmode")
            new_query = urllib.parse.urlencode(q_dict, doseq=True)
            return urllib.parse.urlunsplit((
                "postgresql+asyncpg",
                parsed.netloc,
                parsed.path,
                new_query,
                parsed.fragment,
            ))
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
        if self.DATABASE_URL:
            import urllib.parse
            parsed = urllib.parse.urlsplit(self.DATABASE_URL)
            return urllib.parse.urlunsplit((
                "postgresql+psycopg",
                parsed.netloc,
                parsed.path,
                parsed.query,
                parsed.fragment,
            ))
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
        if self.REDIS_URL:
            return self.REDIS_URL
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
        # LLM path: only real hosted OpenAI (provider=openai, no LLM_BASE_URL)
        # needs a key. 'ollama'/'local' or a custom base_url run keyless.
        llm_key = self.LLM_API_KEY or self.OPENAI_API_KEY
        if (
            (self.LLM_PROVIDER == "openai" and self.LLM_BASE_URL is None)
            or self.LLM_PROVIDER == "openrouter"
        ) and (not llm_key or llm_key == INSECURE_OPENAI_KEY):
            errors.append(
                f"LLM_PROVIDER={self.LLM_PROVIDER} requires a valid API key. "
                "Provide OPENAI_API_KEY or LLM_API_KEY, or set LLM_PROVIDER=ollama / "
                "LLM_PROVIDER=local to run keyless."
            )
        if not self.DATABASE_URL and self.POSTGRES_PASSWORD == INSECURE_POSTGRES_PASSWORD:
            errors.append(
                "POSTGRES_PASSWORD is still the insecure default 'docsmind'; set a real password."
            )
        elif self.DATABASE_URL and f":{INSECURE_POSTGRES_PASSWORD}@" in self.DATABASE_URL:
            errors.append(
                "DATABASE_URL contains the insecure default password 'docsmind'; set a real password."
            )
        return errors


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()