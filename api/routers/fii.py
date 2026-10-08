import logging

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse

from api.dependencies.auth import verify_api_key
from application.use_cases.generate_report_fii import GenerateReportFiiUseCase
from application.use_cases.send_email_report import SendEmailReport
from application.use_cases.predict_valuation_fii import PredictValuationFiiUseCase
from infrastructure.email_service import EmailService
from communication.dtos import (
    SendReportEmailRequest,
    ScheduleReportRequest,
    ValuationPredictionResponse
)

from infrastructure.scheduler_service import SchedulerService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/fiis", tags=["fiis"], dependencies=[Depends(verify_api_key)])

def get_scheduler_service() -> SchedulerService:
    from api.main import scheduler_service
    return scheduler_service

@router.get("/{ticker}/report")
def get_report(
    ticker: str,
) -> FileResponse:
    use_case = GenerateReportFiiUseCase()
    report_path = use_case.execute(ticker)

    if report_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sem anúncios recentes encontrados para {ticker} — impossível gerar relatório.",
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
            detail=f"Não foi possível enviar o relatório por email do {payload.ticker} para {payload.email_to}.",
        )

    return {"message": f"Relatório para {payload.ticker} enviado com sucesso para {payload.email_to}."}

@router.post("/schedule-email", response_model=dict[str, str])
def schedule_monthly_email(
    payload: ScheduleReportRequest,
    scheduler: SchedulerService = Depends(get_scheduler_service),
) -> dict[str, str]:
    """Agenda a tarefa recorrente mensal para gerar e enviar o relatório por e-mail."""
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
        "message": f"Relatório mensal para {payload.ticker} agendado com sucesso para o dia {payload.day_of_month} às {payload.hour}:00."
    }

@router.get(
    "/{ticker}/valuation-prediction",
    response_model=ValuationPredictionResponse,
    summary="Previsão de Preço e Valuation de Curto e Médio Prazo",
)
def predict_valuation(
    ticker: str,
    force_refresh: bool = Query(False, description="Se verdadeiro, ignora o cache mensal e refaz a previsão"),
) -> ValuationPredictionResponse:
    """Endpoint que retorna a análise preditiva unificada (30 dias e 12 meses) com base em RAG e Valuation Financeiro."""
    use_case = PredictValuationFiiUseCase()
    return use_case.execute(ticker=ticker, force_refresh=force_refresh)