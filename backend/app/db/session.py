"""SQLite connection management for the run history."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

SCHEMA_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS runs (
        id           TEXT PRIMARY KEY,
        created_at   TEXT NOT NULL,
        kind         TEXT NOT NULL,
        label        TEXT NOT NULL,
        T_metal_C    REAL NOT NULL,
        Q_platen_MW  REAL NOT NULL,
        m_tph        REAL NOT NULL,
        T_in_C       REAL NOT NULL,
        T_out_C      REAL NOT NULL,
        warnings     TEXT NOT NULL DEFAULT '[]',
        payload      TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_runs_created ON runs(created_at DESC)",
)



class Database:
    """Small SQLite wrapper: one connection per operation, WAL enabled."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialised = False

    def connect(self) -> sqlite3.Connection:
        """Open a connection with sensible defaults."""
        connection = sqlite3.connect(self.path, timeout=10.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Transactional connection scope."""
        connection = self.connect()
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def init_schema(self) -> None:
        """Create tables and indexes when missing."""
        if self._initialised:
            return
        with self.connection() as connection:
            for statement in SCHEMA_STATEMENTS:
                connection.execute(statement)
        self._initialised = True
