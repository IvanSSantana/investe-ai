import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from application.use_cases.generate_report_fii import GenerateReportFiiUseCase
from application.use_cases.get_indicators_fii import GetIndicatorsFiiUseCase
from application.use_cases.send_email_report import SendEmailReport
from infrastructure.email_service import EmailService
from communication.dtos import (
    SendReportEmailRequest,
    ScheduleReportRequest,
    RealStateFundResponse,
)

from infrastructure.scheduler_service import SchedulerService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/fiis", tags=["fiis"])

def get_scheduler_service() -> SchedulerService:
    from api.main import scheduler_service
    return scheduler_service

@router.get("/{ticker}/indicators", response_model=RealStateFundResponse)
def get_indicators(
    ticker: str,
) -> RealStateFundResponse:
    use_case = GetIndicatorsFiiUseCase()
    return use_case.execute(ticker)

@router.get("/{ticker}/report")
def get_report(
    ticker: str,
) -> FileResponse:
    use_case = GenerateReportFiiUseCase()
    report_path = use_case.execute(ticker)

    if report_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No recent announcements found for {ticker} — unable to generate report.",
        )

    return FileResponse(path=report_path, media_type="text/markdown", filename=report_path.name)

@router.post("/send-email", response_model=dict[str, str])
def send_report_email(payload: SendReportEmailRequest) -> dict[str, str]:
    generate_use_case = GenerateReportFiiUseCase()
    email_service = EmailService()
    send_email_use_case = SendEmailReport(use_case=generate_use_case, email_service=email_service)

    success = send_email_use_case.execute(payload.ticker, payload.email_to)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to send report email for {payload.ticker} to {payload.email_to}.",
        )

    return {"message": f"Report for {payload.ticker} sent successfully to {payload.email_to}."}

@router.post("/schedule-email", response_model=dict[str, str])
def schedule_monthly_email(
    payload: ScheduleReportRequest,
    scheduler: SchedulerService = Depends(get_scheduler_service),
) -> dict[str, str]:
    """Schedules a recurring monthly task to generate and send the report by email."""
    generate_use_case = GenerateReportFiiUseCase()
    email_service = EmailService()
    send_use_case = SendEmailReport(use_case=generate_use_case, email_service=email_service)

    scheduler.add_monthly_email_job(
        func=send_use_case.execute,
        ticker=payload.ticker,
        email_to=payload.email_to,
        day_of_month=payload.day_of_month,
        hour=payload.hour,
    )

    return {
        "message": f"Monthly report for {payload.ticker} successfully scheduled for day {payload.day_of_month} at {payload.hour}:00."
    }