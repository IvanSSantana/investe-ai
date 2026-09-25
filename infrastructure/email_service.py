import os
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import markdown

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.port = int(os.getenv("SMTP_PORT", "587"))
        self.user = os.getenv("SMTP_USER")
        self.password = os.getenv("SMTP_PASSWORD")

    def send_report_email(
            self, 
            email_to: str,
            subject: str, 
            markdown_content: str
        ) -> bool:
        
        if not self.user or not self.password:
            logger.error("SMTP credentials are not configured in environment variables.")
            return False

        try:
            html_body = markdown.markdown(markdown_content, extensions=["tables", "fenced_code"])
            
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.user
            msg["To"] = email_to

            part_text = MIMEText(markdown_content, "plain", "utf-8")
            part_html = MIMEText(f"<html><body>{html_body}</body></html>", "html", "utf-8")
            msg.attach(part_text)
            msg.attach(part_html)

            with smtplib.SMTP(self.server, self.port) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.sendmail(self.user, email_to, msg.as_string())

            logger.info(f"Report successfully sent to '{email_to}'.")
            return True
        except Exception as e:
            logger.exception(f"Failed to send email to '{email_to}': {str(e)}")
            return False