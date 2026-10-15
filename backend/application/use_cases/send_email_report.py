import logging
from datetime import datetime
import locale

from application.use_cases.generate_report_fii import GenerateReportFiiUseCase
from infrastructure.email_service import EmailService

logger = logging.getLogger(__name__)

try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except locale.Error:
    logger.warning("Locale 'pt_BR.UTF-8' not available. Falling back to default system locale.")

class SendEmailReport:
    def __init__(
        self,
        use_case: GenerateReportFiiUseCase,
        email_service: EmailService
    ):
        self.use_case = use_case
        self.email_service = email_service

    def execute(self, ticker: str, email_to: str) -> bool:
        logger.info(f"Executing SendEmailReport for ticker={ticker} to={email_to}.")
        
        report_path = self.use_case.execute(ticker)
        
        if report_path is None or not report_path.exists():
            logger.error(f"Failed to send email: Report file for {ticker} was not found or not generated.")
            return False

        markdown_content = report_path.read_text(encoding="utf-8")
        
        subject = f"Investe Aí - Relatório Mensal de {datetime.now().strftime('%B %Y')} - {ticker.upper()}"
        
        return self.email_service.send_report_email(
            email_to=email_to,
            subject=subject,
            markdown_content=markdown_content
        )