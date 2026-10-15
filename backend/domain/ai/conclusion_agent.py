import logging

from agno.agent import Agent
from agno.models.ollama import Ollama
from agno.models.groq import Groq
from agno.tools.yfinance import YFinanceTools

from domain.ai.vectorstore import EventListResponse

logger = logging.getLogger(__name__)

class ConclusionAgent:
    """Generates the report's final conclusion from already-extracted events,
    enriched with market context (historical prices, news and professional recommendations) fetched via YFinanceTools.
    """

    PERSONA = [
        "Você é um analista de fundos imobiliários objetivo e cauteloso.",
        "SEMPRE chame a ferramenta de preço atual e a ferramenta de notícias para o ticker informado "
        "-- isso é obrigatório em toda execução, não uma opção.",
        "Se a busca de notícias não retornar nada relevante para o fundo, trate isso como "
        "resultado normal e não mencione a ausência como se fosse uma falha ou lacuna.",
        "NUNCA force uma relação entre uma notícia e os eventos do relatório se a conexão não "
        "for clara e direta. Não a cite se for o caso de não houver conexão clara e direta.",
        "Cite a notícia relacionada e seu impacto direto para o preço do ativo."
        "Os eventos extraídos do relatório gerencial são a base principal da conclusão; preço, "
        "notícias e recomendações servem apenas como contexto complementar de mercado, nunca substituem ou "
        "inventam eventos novos.",
        "Responda SOMENTE em português do Brasil, de forma curta e objetiva, sem introduções "
        "como 'Aqui está a conclusão'.",
        "Não invente informações que não estejam nos eventos fornecidos ou nos dados retornados pelas ferramentas.",
    ]

    def __init__(self, model_id: str = "qwen3:8b"):
        self._model_id = model_id

    def generate(self, events: EventListResponse, ticker: str) -> str | None:
        if not events:
            return None

        agent = Agent(
            model=Groq(temperature=0.1),
            tools=[
                YFinanceTools(
                    enable_company_news=True,
                    enable_historical_prices=True,
                    enable_analyst_recommendations=True
                )
            ],
            instructions=self.PERSONA,
            markdown=False,
            debug_mode=True,
            debug_level=2
        )

        prompt = (
            f"Ticker do fundo: {ticker}.SA\n\n"
            "Com base exclusivamente nos eventos abaixo e no contexto de mercado que você "
            "buscar, escreva uma conclusão curta sobre os principais efeitos para o fundo e "
            "sua cota.\n\n"
            f"Eventos extraídos do relatório:\n{events}"
        )

        response = agent.run(prompt)
        return response.content