import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo  

logger = logging.getLogger(__name__)

class SchedulerService:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()

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
            func, 
            ticker: str, 
            email_to: str, 
            day_of_month: int = 1, 
            hour: int = 12
        ):
        """Schedules a monthly job for generating and sending a report."""
        job_id = f"monthly_email_{ticker}_{email_to}"
        trigger = CronTrigger(day=day_of_month, hour=hour, minute=0, timezone=ZoneInfo("America/Sao_Paulo"))

        self.scheduler.add_job(
            func,
            trigger=trigger,
            args=[ticker, email_to],
            id=job_id,
            replace_existing=True
        )
        logger.info(f"Job '{job_id}' scheduled for day {day_of_month} at {hour}:00.")