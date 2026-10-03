from decimal import Decimal

from agno.knowledge import Knowledge

from domain.ai.conclusion_agent import ConclusionAgent
from domain.ai.vectorstore import EventListResponse, VectorstoreService
from domain.files.valuation_calculator import ValuationCalculator
from domain.ai.valuation_agent import ValuationAgent

from communication.dtos import ValuationPredictionResponse

class AiService:
    """Coordinates fund event extraction and conclusion generation."""

    EXTRACTION_PROMPT = (
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

    def extract_events_from_fund(self, knowledge_db: Knowledge) -> EventListResponse:
        """Extracts this month's events from the fund scoped knowledge."""
        return self._vectorstore_service.extract_events_from_document(self.EXTRACTION_PROMPT, knowledge_db)

    def generate_conclusion(self, events: EventListResponse, ticker: str) -> str | None:
        """Generates a short conclusion from already extracted events, enriched
        with market context (price, news and professional recommendations) fetched by ConclusionAgent."""
        return self._conclusion_agent.generate(events, ticker)
    
    def predict_valuation(
        self,
        ticker: str,
        current_price: Decimal,
        vp_per_share: Decimal,
        pvp: Decimal,
        recent_dpus: list[Decimal],
        risk_free_rate: Decimal = Decimal("0.105"),
        historical_mean_pvp: Decimal = Decimal("1.0"),
    ) -> ValuationPredictionResponse:
        ticker_upper = ticker.upper()

        quantitative_result = self._valuation_calculator.calculate(
            current_price=current_price,
            vp_per_share=vp_per_share,
            historical_mean_pvp=historical_mean_pvp,
            recent_dpus=recent_dpus,
            risk_free_rate=risk_free_rate,
        )

        db = self._vectorstore_service.build_vectorstore(ticker_upper)
        knowledge = self._vectorstore_service.get_or_create_knowledge(db, ticker_upper)

        return self._valuation_agent.run(
            ticker=ticker_upper,
            current_price=current_price,
            pvp=pvp,
            quantitative_result=quantitative_result,
            knowledge_db=knowledge,
        )