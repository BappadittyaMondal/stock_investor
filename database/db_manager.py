"""
HFOS v5.0 — Database Manager
Handles SQLite with WAL mode, connection pooling, migrations.
PostgreSQL migration path via environment flag.
"""
import sqlite3
import logging
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from config.settings import DB_PATH

logger = logging.getLogger(__name__)

_local = threading.local()


def get_connection() -> sqlite3.Connection:
    """Thread-local SQLite connection with WAL + FK support."""
    if not hasattr(_local, "conn") or _local.conn is None:
        conn = sqlite3.connect(
            DB_PATH,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            check_same_thread=False,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-64000")  # 64 MB page cache
        conn.execute("PRAGMA temp_store=MEMORY")
        _local.conn = conn
    return _local.conn


@contextmanager
def db_transaction() -> Generator[sqlite3.Connection, None, None]:
    """Context manager for explicit transactions with rollback on error."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def close_connection():
    """Close thread-local connection."""
    if hasattr(_local, "conn") and _local.conn:
        _local.conn.close()
        _local.conn = None


def initialize_schema():
    """Create all tables from schema.sql if not already present."""
    schema_path = Path(__file__).parent.parent / "database" / "schema.sql"
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    with open(schema_path, "r", encoding="utf-8") as f:
        sql = f.read()
    conn = get_connection()
    # Execute statement by statement to handle SQLite limitations
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    with conn:
        for stmt in statements:
            try:
                conn.execute(stmt)
            except sqlite3.OperationalError as e:
                if "already exists" not in str(e):
                    logger.error(f"Schema error: {e}\nStatement: {stmt[:200]}")
    logger.info("Database schema initialized successfully")


def execute_query(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    """Execute a SELECT query and return all rows."""
    conn = get_connection()
    cur = conn.execute(sql, params)
    return cur.fetchall()


def execute_one(sql: str, params: tuple = ()) -> sqlite3.Row | None:
    """Execute a SELECT query and return one row."""
    conn = get_connection()
    return conn.execute(sql, params).fetchone()


def execute_write(sql: str, params: tuple = ()) -> int:
    """Execute an INSERT/UPDATE/DELETE and return lastrowid."""
    conn = get_connection()
    with conn:
        cur = conn.execute(sql, params)
        return cur.lastrowid


def execute_many(sql: str, params_list: list[tuple]) -> int:
    """Execute batch INSERT/UPDATE and return rows affected."""
    conn = get_connection()
    with conn:
        cur = conn.executemany(sql, params_list)
        return cur.rowcount


def run_migration(migration_sql: str, migration_name: str):
    """Apply a migration SQL string, idempotent."""
    conn = get_connection()
    # Create migrations tracking table if needed
    conn.execute(
        """CREATE TABLE IF NOT EXISTS _migrations (
            name TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        )"""
    )
    conn.commit()
    row = conn.execute(
        "SELECT 1 FROM _migrations WHERE name=?", (migration_name,)
    ).fetchone()
    if row:
        logger.debug(f"Migration already applied: {migration_name}")
        return
    try:
        with conn:
            conn.executescript(migration_sql)
            conn.execute(
                "INSERT INTO _migrations(name) VALUES(?)", (migration_name,)
            )
        logger.info(f"Migration applied: {migration_name}")
    except Exception as e:
        logger.error(f"Migration failed [{migration_name}]: {e}")
        raise
