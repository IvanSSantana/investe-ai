import sqlite3
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

DB_PATH = Path("auth_db") / "users.db"

class UserRecord(NamedTuple):
    user_id: str
    email: str
    password_hash: str
    created_at: datetime
    active: bool

class UserRepository:
    def __init__(self, db_path: Path = DB_PATH):
        self._db_path = db_path
        self._ensure_schema()

    def create(self, user_id: str, email: str, password_hash: str) -> UserRecord:
        created_at = datetime.now()

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO users (user_id, email, password_hash, created_at, active)
                VALUES (?, ?, ?, ?, 1)
                """,
                (user_id, email.lower(), password_hash, created_at.isoformat()),
            )

        return UserRecord(
            user_id=user_id,
            email=email.lower(),
            password_hash=password_hash,
            created_at=created_at,
            active=True,
        )

    def find_by_email(self, email: str) -> UserRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT user_id, email, password_hash, created_at, active FROM users WHERE email = ?",
                (email.lower(),),
            ).fetchone()

        return self._row_to_record(row) if row else None

    def find_by_id(self, user_id: str) -> UserRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT user_id, email, password_hash, created_at, active FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()

        return self._row_to_record(row) if row else None

    def _connect(self) -> sqlite3.Connection:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")

    @staticmethod
    def _row_to_record(row: tuple) -> UserRecord:
        user_id, email, password_hash, created_at, active = row
        return UserRecord(
            user_id=user_id,
            email=email,
            password_hash=password_hash,
            created_at=datetime.fromisoformat(created_at),
            active=bool(active),
        )