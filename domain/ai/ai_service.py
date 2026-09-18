from agno.knowledge import Knowledge

from domain.ai.ai_client import local_query
from domain.ai.vectorstore import VectorstoreService


class AiService:
    """Coordinates fund event extraction and conclusion generation."""

    EXTRACTION_QUERY = (
        "Quais os eventos mais relevantes ocorridos no último mês para o fundo, "
        "um por categoria? Indique o impacto de cada um no preço da cota."
    )

    CONCLUSION_PERSONA = "Você é um analista de fundos imobiliários objetivo e cauteloso."

    def __init__(self, vectorstore_service: VectorstoreService = VectorstoreService()):
        self._vectorstore_service = vectorstore_service

    def extract_events_from_fund(self, knowledge_db: Knowledge) -> list[dict]:
        """Extracts this month's events from the fund scoped knowledge."""
        return self._vectorstore_service.extract_events_from_document(self.EXTRACTION_QUERY, knowledge_db)

    def generate_conclusion(self, events: list[dict]) -> str | None:
        """Generates a short conclusion from already extracted events."""
        if not events:
            return None

        content = (
            "Com base exclusivamente nos eventos abaixo, escreva uma conclusão "
            "curta em português sobre os principais efeitos para o fundo e sua "
            "cota. Não invente informações.\n"
            f"{events}"
        )
        return local_query(persona=self.CONCLUSION_PERSONA, content=content)