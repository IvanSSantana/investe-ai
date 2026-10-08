import logging

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


@router.get("/{ticker}/history/csv")
def get_price_history_csv(
    ticker: str,
    include_explanation: bool = Query(
        True, description="Se verdadeiro, insere explicações acerca das variações de preço acima de 2.5%"
    ),
    force_refresh: bool = Query(False, description="Se verdadeiro, ignora o cache mensal e gera um novo CSV"),
    has_valid_api_key: bool = Depends(optional_api_key),
) -> FileResponse:
    """
    Gera e retorna um arquivo CSV contendo as variações mensais de preço ao longo de um ano,
    os retornos totais e explicações opcionais de IA para meses com valores atípicos.

    Esta rota é pública. O parâmetro `include_explanation` só tem efeito
    quando uma chave de API válida é enviada no cabeçalho `X-API-Key`; caso contrário,
    a explicação gerada por IA é omitida automaticamente.
    """
    effective_include_explanation = include_explanation and has_valid_api_key

    use_case = ExportPriceHistoryFiiUseCase()
    try:
        csv_path = use_case.execute(
            ticker=ticker,
            include_explanation=effective_include_explanation,
            force_refresh=force_refresh
        )

        return FileResponse(
            path=csv_path,
            media_type="text/csv",
            filename=csv_path.name,
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Histórico de preços para {ticker} não encontrado.",
        )