"""Application settings, read from environment variables (see .env.example)."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://pitchlab:pitchlab@localhost:5432/pitchlab"
    redis_url: str = "redis://localhost:6379/0"
    queue_name: str = "analysis"

    storage_dir: Path = Path("./storage")
    max_upload_bytes: int = 500 * 1024 * 1024
    allowed_video_extensions: tuple[str, ...] = (".mp4", ".mov", ".m4v", ".avi")

    # "fake" returns fixed events after FAKE_ANALYZER_SECONDS (tests, load tests).
    # "real" runs the repository's analyzer scripts (needs MediaPipe in the image).
    analyzer: Literal["fake", "real"] = "fake"
    fake_analyzer_seconds: float = 2.0
    analyzer_repo_dir: Path = Path(__file__).resolve().parents[2]

    job_max_attempts: int = 3
    job_timeout_seconds: int = 900
    retry_base_seconds: float = 2.0
    retry_cap_seconds: float = 300.0

    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
