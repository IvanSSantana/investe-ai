import sqlite3
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

DB_PATH = Path("auth_db") / "api_keys.db"

class ApiKeyRecord(NamedTuple):
    key_id: str
    key_hash: str
    name: str
    created_at: datetime
    expires_at: datetime | None
    active: bool

class ApiKeyRepository:
    """Persists and queries API keys in a local SQLite database.
    """

    def __init__(self, db_path: Path = DB_PATH):
        self._db_path = db_path
        self._ensure_schema()

    def create(
        self,
        key_id: str,
        key_hash: str,
        name: str,
        expires_at: datetime | None,
    ) -> ApiKeyRecord:
        created_at = datetime.now()

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO api_keys (key_id, key_hash, name, created_at, expires_at, active)
                VALUES (?, ?, ?, ?, ?, 1)
                """,
                (key_id, key_hash, name, created_at.isoformat(), expires_at.isoformat() if expires_at else None),
            )

        return ApiKeyRecord(
            key_id=key_id,
            key_hash=key_hash,
            name=name,
            created_at=created_at,
            expires_at=expires_at,
            active=True,
        )

    def find_by_hash(self, key_hash: str) -> ApiKeyRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT key_id, key_hash, name, created_at, expires_at, active FROM api_keys WHERE key_hash = ?",
                (key_hash,),
            ).fetchone()

        return self._row_to_record(row) if row else None

    def revoke(self, key_id: str) -> bool:
        """Soft-revokes a key by setting active=0. Returns False if key_id doesn't exist."""
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE api_keys SET active = 0 WHERE key_id = ?",
                (key_id,),
            )
            return cursor.rowcount > 0

    def _connect(self) -> sqlite3.Connection:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS api_keys (
                    key_id TEXT PRIMARY KEY,
                    key_hash TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT,
                    active INTEGER NOT NULL DEFAULT 1
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash)")

    @staticmethod
    def _row_to_record(row: tuple) -> ApiKeyRecord:
        key_id, key_hash, name, created_at, expires_at, active = row
        return ApiKeyRecord(
            key_id=key_id,
            key_hash=key_hash,
            name=name,
            created_at=datetime.fromisoformat(created_at),
            expires_at=datetime.fromisoformat(expires_at) if expires_at else None,
            active=bool(active),
        )