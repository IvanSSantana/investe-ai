import logging
from pathlib import Path
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger

from infrastructure.scheduled_jobs import run_monthly_email_job
from repository.scheduled_job_repository import ScheduledJobRepository

logger = logging.getLogger(__name__)

_JOBSTORE_DB_PATH = Path("data/investe_ai.db")

class SchedulerService:
    def __init__(self) -> None:
        _JOBSTORE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

        jobstores = {
            "default": SQLAlchemyJobStore(url=f"sqlite:///{_JOBSTORE_DB_PATH}")
        }
        self.scheduler = AsyncIOScheduler(jobstores=jobstores)
        self._job_repository = ScheduledJobRepository()

    def start(self) -> None:
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("APScheduler service started successfully.")

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("APScheduler service stopped.")

    def add_monthly_email_job(
        self,
        ticker: str,
        email_to: str,
        user_id: str,
        day_of_month: int = 1,
        hour: int = 12,
    ) -> None:
        """Schedule a recurring monthly job and record the ownership link (who scheduled it)."""
        job_id = f"monthly_email_{ticker}_{email_to}"
        trigger = CronTrigger(
            day=day_of_month, hour=hour, minute=0, timezone=ZoneInfo("America/Sao_Paulo")
        )

        self.scheduler.add_job(
            run_monthly_email_job,
            trigger=trigger,
            args=[ticker, email_to],
            id=job_id,
            replace_existing=True,
        )

        self._job_repository.record(
            job_id=job_id,
            user_id=user_id,
            ticker=ticker,
            email_to=email_to,
            day_of_month=day_of_month,
            hour=hour,
        )

        logger.info(f"Job '{job_id}' scheduled for day {day_of_month} at {hour}:00 by user '{user_id}'.")

    def remove_job(self, job_id: str, user_id: str) -> bool:
        """Remove the APScheduler job and its history, but only if it belongs to the requesting user."""
        owned_jobs = self._job_repository.list_by_user(user_id)
        if not any(job.job_id == job_id for job in owned_jobs):
            return False

        self.scheduler.remove_job(job_id)
        self._job_repository.delete(job_id)

        logger.info(f"Job '{job_id}' removed by user '{user_id}'.")
        return True

    def list_jobs_by_user(self, user_id: str) -> list:
        return self._job_repository.list_by_user(user_id)