import logging
from zoneinfo import ZoneInfo  

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

from infrastructure.scheduled_jobs import run_monthly_email_job

logger = logging.getLogger(__name__)

JOBS_DB_PATH = "scheduler_jobs.db"

class SchedulerService:
    def __init__(self):
        jobstores = {"default": SQLAlchemyJobStore(url=f"sqlite:///{JOBS_DB_PATH}")}
        self.scheduler = AsyncIOScheduler(jobstores=jobstores)

    def start(self):
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("APScheduler service started successfully.")

    def shutdown(self):
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("APScheduler service stopped.")

    def add_monthly_email_job(
            self, 
            ticker: str, 
            email_to: str, 
            day_of_month: int = 1, 
            hour: int = 12
        ):
        """Schedules a monthly job for generating and sending a report."""
        job_id = f"monthly_email_{ticker}_{email_to}"
        trigger = CronTrigger(day=day_of_month, hour=hour, minute=0, timezone=ZoneInfo("America/Sao_Paulo"))

        self.scheduler.add_job(
            run_monthly_email_job,
            trigger=trigger,
            args=[ticker, email_to],
            id=job_id,
            replace_existing=True
        )
        logger.info(f"Job '{job_id}' scheduled for day {day_of_month} at {hour}:00.")