import secrets
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import NamedTuple

DB_PATH = Path("auth_db") / "sessions.db"
SESSION_DURATION_DAYS = 7

class SessionRecord(NamedTuple):
    session_token: str
    user_id: str
    created_at: datetime
    expires_at: datetime

class SessionRepository:
    def __init__(self, db_path: Path = DB_PATH):
        self._db_path = db_path
        self._ensure_schema()

    def create(self, user_id: str) -> SessionRecord:
        session_token = secrets.token_urlsafe(32)
        created_at = datetime.now()
        expires_at = created_at + timedelta(days=SESSION_DURATION_DAYS)

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sessions (session_token, user_id, created_at, expires_at)
                VALUES (?, ?, ?, ?)
                """,
                (session_token, user_id, created_at.isoformat(), expires_at.isoformat()),
            )

        return SessionRecord(
            session_token=session_token,
            user_id=user_id,
            created_at=created_at,
            expires_at=expires_at,
        )

    def find_by_token(self, session_token: str) -> SessionRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT session_token, user_id, created_at, expires_at FROM sessions WHERE session_token = ?",
                (session_token,),
            ).fetchone()

        return self._row_to_record(row) if row else None

    def delete(self, session_token: str) -> None:
        """Invalidates a session (logout)."""
        with self._connect() as conn:
            conn.execute("DELETE FROM sessions WHERE session_token = ?", (session_token,))

    def _connect(self) -> sqlite3.Connection:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_token TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)")

    @staticmethod
    def _row_to_record(row: tuple) -> SessionRecord:
        session_token, user_id, created_at, expires_at = row
        return SessionRecord(
            session_token=session_token,
            user_id=user_id,
            created_at=datetime.fromisoformat(created_at),
            expires_at=datetime.fromisoformat(expires_at),
        )