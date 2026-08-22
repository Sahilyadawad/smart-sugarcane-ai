"""Application configuration.

Every path in the project is derived from PROJECT_ROOT so the backend works the
same whether uvicorn is started from ``backend/`` or from the repository root.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# config.py -> core -> app -> backend -> <project root>
PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = PROJECT_ROOT / "backend"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR / ".env", PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- General ---
    APP_NAME: str = "Smart Sugarcane AI"
    APP_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    DEBUG: bool = True

    # --- Security ---
    SECRET_KEY: str = "dev-only-insecure-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    # --- Database ---
    DATABASE_URL: str = ""

    # --- CORS ---
    # Kept as a plain string, not List[str], on purpose. pydantic-settings tries
    # to JSON-decode complex types read from a .env file *before* any validator
    # runs, so a comma-separated value raises SettingsError instead of reaching
    # a `mode="before"` validator. Parsing happens in `cors_origins` below.
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173"

    # --- Uploads ---
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_MB: int = 10

    # Serverless platforms (Vercel, Lambda) give the function a read-only
    # filesystem, so saving uploads is impossible there. Leave unset to
    # auto-detect; set explicitly to override.
    PERSIST_UPLOADS: bool | None = None

    # --- ML ---
    # demo | production | auto
    MODEL_MODE: str = "auto"

    # --- Weather ---
    OPENWEATHER_API_KEY: str = ""
    DEFAULT_WEATHER_CITY: str = "Belagavi,IN"

    @field_validator("MODEL_MODE", mode="before")
    @classmethod
    def _normalise_mode(cls, value):
        allowed = {"demo", "production", "auto"}
        text = str(value or "auto").strip().lower()
        return text if text in allowed else "auto"

    @property
    def is_serverless(self) -> bool:
        """True on platforms that give the function a read-only filesystem."""
        return bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"))

    @property
    def persist_uploads(self) -> bool:
        """Whether uploaded images can be written to disk and served back."""
        if self.PERSIST_UPLOADS is not None:
            return self.PERSIST_UPLOADS
        return not self.is_serverless

    @property
    def cors_origins(self) -> List[str]:
        """Allowed frontend origins, parsed from the comma-separated setting."""
        return [item.strip() for item in self.CORS_ORIGINS.split(",") if item.strip()]

    # ------------------------------------------------------------------ paths
    @property
    def project_root(self) -> Path:
        return PROJECT_ROOT

    @property
    def data_dir(self) -> Path:
        return PROJECT_ROOT / "data"

    @property
    def models_dir(self) -> Path:
        return PROJECT_ROOT / "models"

    @property
    def upload_path(self) -> Path:
        raw = Path(self.UPLOAD_DIR)
        return raw if raw.is_absolute() else PROJECT_ROOT / raw

    @property
    def database_uri(self) -> str:
        """Absolute SQLite URI by default so the DB file never moves around."""
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            # Turn a relative sqlite path into an absolute one.
            if url.startswith("sqlite:///./"):
                relative = url.replace("sqlite:///./", "", 1)
                return f"sqlite:///{(BACKEND_DIR / relative).as_posix()}"
            return url

        if self.is_serverless:
            # The deployment directory is read-only, so the normal location
            # cannot be created and SQLAlchemy would fail at startup. /tmp is
            # the one writable path, which at least lets the app boot and
            # report the real problem instead of returning
            # FUNCTION_INVOCATION_FAILED for every route.
            #
            # This storage does NOT persist between invocations. Set
            # DATABASE_URL to a hosted Postgres for anything real.
            return "sqlite:////tmp/smart_sugarcane.db"

        return f"sqlite:///{(BACKEND_DIR / 'smart_sugarcane.db').as_posix()}"

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_MB * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    # Create the directories the app writes to. On a read-only serverless
    # filesystem this is both impossible and unnecessary, and an unguarded
    # mkdir here would crash the app at import time.
    if settings.persist_uploads:
        try:
            for sub in ("plants", "soil"):
                (settings.upload_path / sub).mkdir(parents=True, exist_ok=True)
            settings.models_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            # Filesystem turned out to be read-only after all - degrade instead
            # of taking the whole application down.
            settings.PERSIST_UPLOADS = False
    return settings


settings = get_settings()
