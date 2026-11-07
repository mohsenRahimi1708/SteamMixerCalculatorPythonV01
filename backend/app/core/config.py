"""Runtime configuration (environment driven, 12-factor)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Service settings; every field can be overridden with a ``PST_`` env var."""

    model_config = SettingsConfigDict(
        env_prefix="PST_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "Platen Superheater Digital Twin"
    db_path: str = "data/platensh.db"
    cors_origins: list[str] = ["*"]
    rate_limit_per_minute: int = 240
    ws_frame_interval_s: float = 0.2
    live_dt_s: float = 0.5
    default_speed: float = 10.0
    max_transient_steps: int = 20000
    log_level: str = "INFO"

    def resolved_db_path(self) -> Path:
        """Absolute database path, creating its directory when needed."""
        path = Path(self.db_path)
        if not path.is_absolute():
            path = Path(__file__).resolve().parents[2] / path
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()


settings = get_settings()
