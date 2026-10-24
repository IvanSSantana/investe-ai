import logging
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, status, Depends
from fastapi.responses import FileResponse

from api.dependencies.auth import optional_api_key
from application.use_cases.export_price_history_fii import ExportPriceHistoryFiiUseCase
from application.use_cases.get_indicators_fii import GetIndicatorsFiiUseCase
from communication.dtos import RealStateFundResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/fiis", tags=["fiis-public"])

@router.get("/{ticker}/indicators", response_model=RealStateFundResponse)
def get_indicators(
    ticker: str,
    force_refresh: bool = Query(False, description="Se verdadeiro, ignora o cache diário e refaz o scraping"),
):
    use_case = GetIndicatorsFiiUseCase()
    return use_case.execute(ticker=ticker, force_refresh=force_refresh)

@router.get("/{ticker}/history", response_model=list[dict[str, Any]])
def get_price_history(
    ticker: str,
    output_type: Literal["csv", "json"] = Query(
        "json", description="'json' (period=5y) ou 'csv' (period=1y)."
    ),
    include_explanation: bool = Query(True),
    force_refresh: bool = Query(False),
    has_valid_api_key: bool = Depends(optional_api_key),
) -> Any:
    effective_include_explanation = include_explanation and has_valid_api_key and output_type != "json"
    use_case = ExportPriceHistoryFiiUseCase()

    try:
        result = use_case.execute(
            ticker=ticker,
            include_explanation=effective_include_explanation,
            force_refresh=force_refresh,
            output_type=output_type,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Histórico de preços para {ticker} não encontrado.",
        )

    if output_type == "csv":
        return FileResponse(
            path=result,  # type: ignore[arg-type]
            media_type="text/csv",
            filename=Path(result).name,  # type: ignore[arg-type]
        )
    return result