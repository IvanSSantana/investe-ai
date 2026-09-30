import logging
from typing import Any

from agno.agent import Agent
from agno.models.ollama import Ollama
from agno.knowledge import Knowledge
from duckduckgo_search import DDGS

from domain.ai.vectorstore import VectorstoreService

logger = logging.getLogger(__name__)

class VariationExplainAgent:
    """Agno Agent responsible for analyzing and explaining significant FII price variations."""

    def __init__(
        self,
        vectorstore_service: VectorstoreService = VectorstoreService(),
    ):
        self._vectorstore_service = vectorstore_service 
        self._agent = Agent(
            model=Ollama(id="qwen3:8b", options={"temperature": 0.17}),
            instructions=[
                "Você é um analista financeiro sênior especializado em Fundos Imobiliários (FIIs) no Brasil.",
                "Sua tarefa é explicar sucintamente o motivo da variação atípica do preço de um FII em um mês específico.",
                "Instruções de Resposta:",
                "1. Forneça uma explicação objetiva e direta de no máximo 2 frases.",
                "2. Baseie-se primeiramente nos fatos informados do contexto (relatórios, notícias ou cenário econômico da época).",
                "3. Se o contexto for muito limitado, informe SOMENTE: 'Insuficiência de dados para explicação.'.",
                "4. Responda estritamente em português.",
            ],
            debug_mode=True,
            debug_level=2
        )

    def explain_month(
        self,
        ticker: str,
        month_data: dict[str, Any],
        knowledge_db: Knowledge | None = None,
    ) -> str:
        year_month = month_data["year_month"]
        price_var = month_data["price_variation_percent"]
        dividends = month_data["dividends_paid"]

        logger.info(f"Generating AI explanation for {ticker} - {year_month} (Variation: {price_var}%)")

        context = self._fetch_context(ticker, year_month, knowledge_db)

        prompt = f"""
        Analise a variação do FII {ticker.upper()} no período de {year_month}:
        - Variação do Preço da Cota: {price_var}%
        - Proventos Pagos no Mês: R$ {dividends}

        Contexto de Relatórios e Notícias do Período:
        {context if context else 'Sem dados específicos de notícias disponíveis.'}

        Gere a justificativa sucinta para esta variação.
        """

        try:
            response = self._agent.run(prompt)
            return response.content.strip() if hasattr(response, "content") else str(response).strip() # type: ignore
        except Exception as e:
            logger.error(f"Failed to generate explanation via Agno agent for {ticker} {year_month}: {e}")
            return "Variação atípica sem justificativa clara nos relatórios do período."

    def _fetch_context(
        self, ticker: str, year_month: str, knowledge_db: Knowledge | None = None
    ) -> str:
        """Retrieves context using vectorstore RAG or falls back to DDG Web Search."""
        query = f"fatos relevantes motivo oscilacao rendimentos {ticker} {year_month}"

        context = ""
        if knowledge_db:
            try:
                events = self._vectorstore_service.extract_events_from_document(query, knowledge_db)
                if events:
                    context = "\n".join([str(e) for e in events])
            except Exception as e:
                logger.warning(f"Failed to query vectorstore for {ticker} {year_month}: {e}")

        if len(context.strip()) < 80:
            logger.info(f"Fallback to DuckDuckGo search for {ticker} {year_month}")
            try:
                ddgs = DDGS()
                results = list(ddgs.text(f"{ticker} mercado motivo cota {year_month}", max_results=5))
                snippets = [r.get("body", "") for r in results if r.get("body")]
                if snippets:
                    context += "\nNotícias da Web:\n" + "\n".join(snippets)
            except Exception as e:
                logger.warning(f"DuckDuckGo search failed: {e}")

        return context.strip()