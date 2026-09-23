from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from application.use_cases.generate_report_fii import GenerateReportFiiUseCase
from application.use_cases.get_indicators_fii import GetIndicatorsFiiUseCase
from communication.dtos import RealStateFundResponse

router = APIRouter(prefix="/api/v1/fiis", tags=["fiis"])

@router.get("/{ticker}/indicators", response_model=RealStateFundResponse)
def get_indicators(
    ticker: str,
    use_case: GetIndicatorsFiiUseCase,
) -> RealStateFundResponse:
    return use_case.execute(ticker)

@router.get("/{ticker}/report")
def get_report(
    ticker: str,
    use_case: GenerateReportFiiUseCase,
) -> FileResponse:
    report_path = use_case.execute(ticker)

    if report_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No recent announcements found for {ticker} — unable to generate report.",
        )

    return FileResponse(path=report_path, media_type="text/markdown", filename=report_path.name)