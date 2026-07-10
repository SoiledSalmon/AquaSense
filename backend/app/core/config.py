"""Application configuration loaded from environment variables.

Uses Pydantic BaseSettings — every secret is read from env vars or .env,
never hardcoded.
"""

import os
from functools import lru_cache

from pydantic import AliasChoices, Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
env_file_path = os.path.join(backend_dir, ".env")


class Settings(BaseSettings):
    """Typed, validated configuration for the AquaSense backend."""

    model_config = SettingsConfigDict(
        env_file=env_file_path,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Supabase ──────────────────────────────────────
    SUPABASE_URL: str
    SUPABASE_KEY: str  # anon / public key
    SUPABASE_SERVICE_ROLE_KEY: str = Field(
        validation_alias=AliasChoices(
            "supabase_service_role_key",
            "SUPABASE_SERVICE_ROLE_KEY",
            "supabase_service_key",
            "SUPABASE_SERVICE_KEY",
        )
    )  # backend-only — never exposed
    SUPABASE_JWT_SECRET: str  # for JWT signature verification

    # ── ThingSpeak ────────────────────────────────────
    # ThingSpeak MQTT requires 3 credentials: Client ID, Username, Password
    # Generate them at ThingSpeak > Devices > MQTT > Add a new device
    THINGSPEAK_MQTT_CLIENT_ID: str = ""  # Falls back to MQTT_USER if empty
    THINGSPEAK_MQTT_USER: str
    THINGSPEAK_MQTT_API_KEY: str
    THINGSPEAK_REST_API_KEY: str = ""  # Optional fallback for REST catch-up

    # ── Application ───────────────────────────────────
    FRONTEND_URL: str = "http://localhost:3000"
    ENVIRONMENT: str = "development"  # development | staging | production

    # ── Derived ───────────────────────────────────────
    @computed_field  # type: ignore[prop-decorator]
    @property
    def CORS_ORIGINS(self) -> list[str]:
        """Allow-list built from FRONTEND_URL — no wildcards."""
        origins = [self.FRONTEND_URL]
        if self.ENVIRONMENT == "development":
            origins.append("http://localhost:3000")
            origins.append("http://localhost:3001")
        # Deduplicate while preserving order
        return list(dict.fromkeys(origins))

    @computed_field  # type: ignore[prop-decorator]
    @property
    def IS_PRODUCTION(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton settings instance — cached after first call."""
    return Settings()  # type: ignore[call-arg]
