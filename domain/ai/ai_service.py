from agno.knowledge import Knowledge

from domain.ai.conclusion_agent import ConclusionAgent
from domain.ai.vectorstore import VectorstoreService
from domain.files.valuation_calculator import ValuationCalculator
from domain.ai.valuation_agent import ValuationAgent

from communication.dtos import ValuationPredictionResponse

class AiService:
    """Coordinates fund event extraction and conclusion generation."""

    EXTRACTION_QUERY = (
        "Quais ações, decisões ou ocorrências NOVAS o fundo realizou ou sofreu especificamente "
        "no período coberto por este relatório gerencial -- por exemplo, compra ou venda de "
        "imóvel, renegociação ou rescisão de contrato de locação, emissão de cotas, mudança de "
        "gestor, captação de recursos? Ignore informações descritivas ou estruturais do fundo "
        "que não mudam mês a mês (estratégia geral, composição histórica, definição de segmento)."
    )

    def __init__(
        self,
        vectorstore_service: VectorstoreService = VectorstoreService(),
        conclusion_agent: ConclusionAgent = ConclusionAgent(),
        valuation_agent: ValuationAgent = ValuationAgent(),
        valuation_calculator: ValuationCalculator = ValuationCalculator(),
    ):
        self._vectorstore_service = vectorstore_service
        self._conclusion_agent = conclusion_agent
        self._valuation_agent = valuation_agent
        self._valuation_calculator = valuation_calculator

    def extract_events_from_fund(self, knowledge_db: Knowledge) -> list[dict]:
        """Extracts this month's events from the fund scoped knowledge."""
        return self._vectorstore_service.extract_events_from_document(self.EXTRACTION_QUERY, knowledge_db)

    def generate_conclusion(self, events: list[dict], ticker: str) -> str | None:
        """Generates a short conclusion from already extracted events, enriched
        with market context (price, news and professional recommendations) fetched by ConclusionAgent."""
        return self._conclusion_agent.generate(events, ticker)
    
    def predict_valuation(
        self,
        ticker: str,
        current_price: float,
        vp_per_share: float,
        pvp: float,
        recent_dpus: list[float],
        historical_mean_pvp: float = 1.0,
    ) -> ValuationPredictionResponse:
        ticker_upper = ticker.upper()

        quantitative_result = self._valuation_calculator.calculate(
            current_price=current_price,
            vp_per_share=vp_per_share,
            historical_mean_pvp=historical_mean_pvp,
            recent_dpus=recent_dpus,
        )

        db = self._vectorstore_service.build_vectorstore(ticker_upper)
        knowledge = self._vectorstore_service.get_or_create_knowledge(db, ticker_upper)

        return self._valuation_agent.run(
            ticker=ticker_upper,
            current_price=current_price,
            pvp=pvp,
            quant_result=quantitative_result,
            knowledge_db=knowledge,
        )