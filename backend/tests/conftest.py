"""Shared fixtures (agent-written).

Tests use REAL Postgres and Redis (integration tests), configured with:
  TEST_DATABASE_URL  default postgresql+psycopg://pitchlab:pitchlab@localhost:5432/pitchlab_test
  TEST_REDIS_URL     default redis://localhost:6379/15
The test database is created if missing and migrated to head once per run; every
test starts with empty tables and an empty queue.
"""

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

TEST_DB = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://pitchlab:pitchlab@localhost:5432/pitchlab_test"
)
TEST_REDIS = os.environ.get("TEST_REDIS_URL", "redis://localhost:6379/15")
os.environ.update(
    {
        "DATABASE_URL": TEST_DB,
        "REDIS_URL": TEST_REDIS,
        "QUEUE_NAME": "analysis_test",
        "ANALYZER": "fake",
        "FAKE_ANALYZER_SECONDS": "0",
        "LOG_LEVEL": "WARNING",
    }
)

import pytest  # noqa: E402
from sqlalchemy import create_engine, inspect, text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402


def _ensure_database(url: str) -> None:
    parsed = make_url(url)
    admin = create_engine(parsed.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = :n"),
                              {"n": parsed.database}).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{parsed.database}"'))
    admin.dispose()


def run_migrations(url: str, revision: str = "head", downgrade: bool = False) -> None:
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    cfg.attributes["database_url"] = url
    cfg.attributes["configure_logger"] = False
    (command.downgrade if downgrade else command.upgrade)(cfg, revision)


@pytest.fixture(scope="session")
def database_url(tmp_path_factory):
    _ensure_database(TEST_DB)
    engine = create_engine(TEST_DB)
    with engine.begin() as conn:  # start from a clean schema every run
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
    engine.dispose()
    run_migrations(TEST_DB)
    return TEST_DB


@pytest.fixture(autouse=True)
def _settings(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path / "storage"))
    from app.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def clean_db(database_url):
    from app.db import reset_engine

    reset_engine()
    engine = create_engine(database_url)
    tables = [t for t in inspect(engine).get_table_names() if t != "alembic_version"]
    if tables:
        with engine.begin() as conn:
            conn.execute(text(f"TRUNCATE {', '.join(tables)} RESTART IDENTITY CASCADE"))
    engine.dispose()
    yield database_url
    reset_engine()


@pytest.fixture
def db(clean_db):
    from app.db import session_factory

    session = session_factory()()
    yield session
    session.close()


@pytest.fixture
def redis_conn():
    from app.queue import get_redis, reset_redis

    reset_redis()
    conn = get_redis()
    conn.flushdb()
    yield conn
    conn.flushdb()
    reset_redis()


@pytest.fixture
def client(clean_db, redis_conn):
    from fastapi.testclient import TestClient

    from app.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def queued_job_ids(redis_conn):
    """Callable returning job ids currently waiting in the queue (immediate + scheduled)."""

    def _ids() -> list[int]:
        from rq.registry import ScheduledJobRegistry

        from app.queue import get_queue

        queue = get_queue()
        jobs = list(queue.get_jobs())
        registry = ScheduledJobRegistry(queue=queue)
        jobs += [queue.fetch_job(job_id) for job_id in registry.get_job_ids()]
        return sorted(int(job.args[0]) for job in jobs if job is not None)

    return _ids


def make_video_bytes(tag: str = "a", size: int = 2048) -> bytes:
    """Fake 'video' content. The fake analyzer never decodes it."""
    return (tag.encode() * size)[:size]
