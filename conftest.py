"""
HFOS v5.0 — conftest.py (root pytest configuration)
Provides shared fixtures, DB isolation, and path setup.
"""
import os
import sys
import pytest
from pathlib import Path

# Ensure project root is on sys.path for all tests
sys.path.insert(0, str(Path(__file__).parent))


@pytest.fixture(scope="session")
def tmp_db(tmp_path_factory) -> str:
    """
    Session-scoped isolated SQLite DB.
    Sets DB_PATH env var so all modules use the test DB.
    """
    db_file = str(tmp_path_factory.mktemp("hfos_test_db") / "hfos_test.db")
    os.environ["DB_PATH"] = db_file
    # Bootstrap schema into the test DB
    from database.db_manager import initialize_schema
    initialize_schema()
    return db_file


@pytest.fixture(autouse=True)
def reset_thread_local_conn(tmp_db):
    """
    Force reconnect after each test to avoid stale thread-local
    connections pointing at a partially committed state.
    """
    from database import db_manager
    db_manager.close_connection()
    yield
    db_manager.close_connection()


@pytest.fixture(scope="session", autouse=True)
def set_test_env():
    """Set minimal env vars for all tests."""
    os.environ.setdefault("HFOS_JWT_SECRET", "a" * 64)
    os.environ.setdefault("ANTHROPIC_API_KEY", "")
    os.environ.setdefault("TELEGRAM_BOT_TOKEN", "")
    os.environ.setdefault("SMTP_EMAIL", "")
    os.environ.setdefault("SMTP_PASSWORD", "")
    yield
