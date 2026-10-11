import logging

logger = logging.getLogger(__name__)

def run_monthly_email_job(ticker: str, email_to: str) -> None:
    """Serializable entry point for the scheduled job: recreate its dependencies
    at execution time instead of depending on a prebuilt object."""
    from application.use_cases.generate_report_fii import GenerateReportFiiUseCase
    from application.use_cases.send_email_report import SendEmailReport
    from infrastructure.email_service import EmailService

    logger.info(f"Running scheduled monthly email job for ticker={ticker} to={email_to}.")

    use_case = SendEmailReport(
        use_case=GenerateReportFiiUseCase(),
        email_service=EmailService(),
    )
    success = use_case.execute(ticker, email_to)

    if not success:
        logger.error(f"Scheduled monthly email job failed for ticker={ticker} to={email_to}.")