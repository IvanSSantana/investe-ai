import sqlite3
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

DB_PATH = Path("auth_db") / "scheduled_jobs.db"

class ScheduledJobRecord(NamedTuple):
    job_id: str
    user_id: str
    ticker: str
    email_to: str
    day_of_month: int
    hour: int
    created_at: datetime

class ScheduledJobRepository:
    """Tracks which user created each recurring email job, for history/listing purposes.
    The actual scheduling/execution is handled separately by APScheduler.
    """

    def __init__(self, db_path: Path = DB_PATH):
        self._db_path = db_path
        self._ensure_schema()

    def record(
        self,
        job_id: str,
        user_id: str,
        ticker: str,
        email_to: str,
        day_of_month: int,
        hour: int,
    ) -> ScheduledJobRecord:
        created_at = datetime.now()

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO scheduled_jobs (job_id, user_id, ticker, email_to, day_of_month, hour, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    day_of_month = excluded.day_of_month,
                    hour = excluded.hour,
                    created_at = excluded.created_at
                """,
                (job_id, user_id, ticker, email_to, day_of_month, hour, created_at.isoformat()),
            )

        return ScheduledJobRecord(
            job_id=job_id,
            user_id=user_id,
            ticker=ticker,
            email_to=email_to,
            day_of_month=day_of_month,
            hour=hour,
            created_at=created_at,
        )

    def list_by_user(self, user_id: str) -> list[ScheduledJobRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT job_id, user_id, ticker, email_to, day_of_month, hour, created_at
                FROM scheduled_jobs WHERE user_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,),
            ).fetchall()

        return [self._row_to_record(row) for row in rows]

    def delete(self, job_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM scheduled_jobs WHERE job_id = ?", (job_id,))

    def _connect(self) -> sqlite3.Connection:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scheduled_jobs (
                    job_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    email_to TEXT NOT NULL,
                    day_of_month INTEGER NOT NULL,
                    hour INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_scheduled_jobs_user ON scheduled_jobs(user_id)")

    @staticmethod
    def _row_to_record(row: tuple) -> ScheduledJobRecord:
        job_id, user_id, ticker, email_to, day_of_month, hour, created_at = row
        return ScheduledJobRecord(
            job_id=job_id,
            user_id=user_id,
            ticker=ticker,
            email_to=email_to,
            day_of_month=day_of_month,
            hour=hour,
            created_at=datetime.fromisoformat(created_at),
        )