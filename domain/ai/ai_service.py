from agno.knowledge import Knowledge

from domain.ai.conclusion_agent import ConclusionAgent
from domain.ai.vectorstore import VectorstoreService


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
    ):
        self._vectorstore_service = vectorstore_service
        self._conclusion_agent = conclusion_agent

    def extract_events_from_fund(self, knowledge_db: Knowledge) -> list[dict]:
        """Extracts this month's events from the fund scoped knowledge."""
        return self._vectorstore_service.extract_events_from_document(self.EXTRACTION_QUERY, knowledge_db)

    def generate_conclusion(self, events: list[dict], ticker: str) -> str | None:
        """Generates a short conclusion from already extracted events, enriched
        with market context (price, news and professional recommendations) fetched by ConclusionAgent."""
        return self._conclusion_agent.generate(events, ticker)