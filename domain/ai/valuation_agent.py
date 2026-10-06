import json
import logging
from decimal import Decimal

from agno.agent import Agent
from agno.knowledge import Knowledge
from agno.models.ollama import Ollama
from agno.models.groq import Groq
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.yfinance import YFinanceTools

from communication.dtos import QuantitativeValuationResult, ValuationPredictionResponse
from helpers.ai.ai_json_sanitizer import ai_json_sanitizer
from helpers.ai.json_prompt import PROMPT

logger = logging.getLogger(__name__)

class ValuationAgent:
    """Agent responsible for fusing quantitative metrics, report RAG, and market web searches."""

    VALUATION_INSTRUCTIONS = [
        "Você é um analista sênior de Fundos de Investimento Imobiliário (FIIs).",
        "Sua tarefa é sintetizar uma recomendação e predição de preço unificando dados quantitativos, relatórios gerenciais e notícias recentes.",
        "Utilize a ferramenta de busca para encontrar notícias recentes sobre o fundo e a taxa Selic.",
        "Sempre considere o preço justo calculado pelo DDM e pela reversão do P/VP como âncoras numéricas centrais.",
        "Para a projeção de curto prazo (30 dias), analise a regularidade do dividendo e eventos iminentes (vacância, rescisão, venda de imóveis).",
        "Para o médio prazo (12M), defina uma faixa de preço justo [min, max] baseada no P/VP de equilíbrio e DDM.",
        "NUNCA invente dividendos ou cotações que não estejam no contexto recebido.",
        "Retorne ESTRITAMENTE o JSON correspondente ao schema especificado.",
        "Siga SEMPRE o esquema a seguir: \n",
        """Retorne um objeto ValuationPredictionResponse com a seguinte estrutura:

        {
        "ticker": "Código do FII",
        "preco_atual": "Preço atual em R$",
        "pvp_atual": "P/VP atual",

        "curto_prazo": {
            "estimativa_proximo_rendimento": "Próximo dividendo estimado por cota em R$",
            "yield_mensal_estimado_percent": "Dividend Yield mensal estimado em %",
            "tendencia_30d": "Alta, Neutra ou Baixa",
            "gatilhos_imediatos": ["Fatos com impacto no curto prazo"]
        },

        "medio_prazo": {
            "preco_justo_min": "Limite inferior do preço justo em 12 meses (R$)",
            "preco_justo_max": "Limite superior do preço justo em 12 meses (R$)",
            "upside_downside_percent": "Potencial de valorização ou desvalorização em %",
            "tendencia_12m": "Alta, Neutra ou Baixa",
            "tese_investimento": "Síntese da tese baseada em valuation, DRE e mercado"
        },

        "sinal_recomendacao": "Compra Forte, Compra, Aguardar/Neutro ou Venda",
        "riscos_monitorados": ["Principais riscos identificados"]
        }

        REGRAS:
        - Respeite exatamente os nomes e a hierarquia dos campos.
        - Todos os valores numéricos devem ser retornados como números, sem símbolos monetários ou unidades.
        - Listas devem ser retornadas como arrays de strings.
        - Não invente dados ou indicadores ausentes nas fontes.
        - Mantenha as tendências e recomendações dentro das opções especificadas.
        - Retorne exclusivamente o objeto estruturado, sem explicações adicionais.
        """
    ]

    def run(
        self,
        ticker: str,
        current_price: Decimal,
        pvp: Decimal,
        quantitative_result: QuantitativeValuationResult,
        knowledge_db: Knowledge,
    ) -> ValuationPredictionResponse:
        """Executes the valuation agent synthesis."""
        logger.info(f"Running ValuationAgent for {ticker}...")

        agent = Agent(
            role="Analista de Valuation de FIIs",
            knowledge=knowledge_db,
            search_knowledge=True,
            tools=[DuckDuckGoTools(fixed_max_results=3), YFinanceTools(enable_analyst_recommendations=True)],
            add_knowledge_to_context=True,
            instructions=self.VALUATION_INSTRUCTIONS,
            model=Groq(temperature=0.1),
            # output_schema=ValuationPredictionResponse,
            debug_mode=True,
            debug_level=2
        )

        prompt = (
            f"Elabore o relatório preditivo e valuation para o FII {ticker}.\n\n"
            f"DADOS NUMÉRICOS ATUAIS:\n"
            f"- Preço Atual: R$ {current_price}\n"
            f"- P/VP Atual: {pvp}\n"
            f"- DPU Anualizado Estimado: R$ {quantitative_result.annualized_dpu}\n"
            f"- Preço Justo DDM (Desconto de Dividendos): R$ {quantitative_result.ddm_fair_price}\n"
            f"- Preço Teórico por Reversão P/VP: R$ {quantitative_result.pvp_mean_reversion_price}\n"
            f"- Spread de Yield vs Taxa de Desconto: {quantitative_result.yield_spread_percent}%\n\n"
            f"Instrução: Consulte o RAG do relatório gerencial do {ticker} e busque na web notícias recentes para concluir o schema."
        )

        response = agent.run(prompt)
        raw_response_text = str(response.content)

        clean_json = ai_json_sanitizer(raw_response_text)
        
        return ValuationPredictionResponse.model_validate_json(clean_json)