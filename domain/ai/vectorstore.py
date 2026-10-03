import json
import logging
from pathlib import Path
from datetime import datetime

from agno.vectordb.chroma import ChromaDb, SearchType
from agno.knowledge import Knowledge
from agno.knowledge.embedder.ollama import OllamaEmbedder
from agno.knowledge.reader.docling_reader import DoclingReader
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.document_converter import DocumentConverter, PdfFormatOption

from agno.agent import Agent
from agno.models.ollama import Ollama
from agno.models.groq import Groq
from pydantic import BaseModel, Field

from helpers.ai.ai_json_sanitizer import ai_json_sanitizer
from helpers.ai.json_prompt import PROMPT

logger = logging.getLogger(__name__)

class EventResponse(BaseModel):
    titulo: str = Field(
        ...,
        description=(
            "Titulo do evento no formato fixo 'Ação: Detalhe específico' -- "
            "ex.: 'Aquisição de imóvel: Shopping Park Sul', 'Renegociação de contrato: "
            "Locatário XPTO'. NUNCA um título genérico como 'Resultado do fundo'."
        ),
    )
    descricao: str = Field(..., description="Descricao do evento corporativo extraido do documento.")
    impacto: str = Field(..., description="Impacto do evento corporativo no preco da acao da empresa.")
    importancia: int = Field(..., ge=1, le=10, description="1 = Altíssimo impacto econômico, 10 = Impacto praticamente nulo.")
    categoria: str = Field(..., description="Categoria do evento (entre as 10 fornecidas)")

class EventListResponse(BaseModel):
    eventos: list[EventResponse]

FII_MANAGEMENT_REPORT_CATEGORIES = [
    "Distribuição de rendimentos e dividend yield do mês",
    "Resultado financeiro e contábil do período (receita, lucro, FFO)",
    "Carteira de ativos: aquisições, vendas e composição atual",
    "Vacância física e financeira, e negociações de locação/renovação",
    "Inadimplência e revisão de contratos com locatários",
    "Endividamento, alavancagem e custo de dívida do fundo",
    "Captação de recursos, emissão de cotas e ofertas públicas",
    "Valor patrimonial da cota e valorização/desvalorização de mercado",
    "Eventos societários e de gestão (troca de gestor, taxa de administração, assembleias com decisão relevante)",
    "Riscos jurídicos, regulatórios ou contratuais em aberto",
]

CATEGORIES_STR = "CATEGORIAS:\n"
for category in FII_MANAGEMENT_REPORT_CATEGORIES:
    CATEGORIES_STR += f"- {category}\n"

class VectorstoreService:
    """Manages the vector index (ChromaDB) used in agentic RAG extraction:
    builds the DB, inserts documents (fine-grained chunks via SemanticChunking), and
    runs the event extraction agent.
    """

    schema_str = json.dumps(
            EventListResponse.model_json_schema(), 
            ensure_ascii=False, 
            indent=2
        )

    EXTRACTION_INSTRUCTIONS = [
        "# PAPEL",
        "Você extrai eventos corporativos de relatórios gerenciais de FIIs para investidores.",

        "# O QUE É UM EVENTO",
        "Uma ação, decisão ou ocorrência NOVA do período coberto por ESTE relatório.",
        "Exemplos: compra/venda de imóvel nomeado, renegociação ou rescisão de contrato com "
        "locatário nomeado, emissão de cotas, mudança de gestor, captação de recursos, litígio novo.",
        "Preserve todos os valores numéricos, percentuais, datas e nomes citados no texto.",

        "# O QUE NÃO É UM EVENTO",
        "Informação descritiva ou estrutural que não muda mês a mês (segmento do fundo, "
        "estratégia geral, composição histórica).",
        "Nomes de pessoas, cargos, eleições, assembleias ou comunicados protocolares sem "
        "consequência econômica objetiva e material.",

        "# FORMATO DO TÍTULO",
        "SEMPRE 'Ação: Detalhe específico'. NUNCA um título genérico.",
        "Correto: 'Aquisição de imóvel: Shopping Park Sul'. Errado: 'Resultado do fundo'.",

        "# REGRA MAIS IMPORTANTE",
        "Uma lista vazia é SEMPRE preferível a um evento inventado, genérico ou descritivo. "
        "Se nenhum evento do texto se encaixar nas regras acima, retorne eventos: [].",

        "# OUTRAS REGRAS",
        "Extraia ATÉ 10 eventos, no máximo 1 por categoria, mais relevantes e impactantes.",
        "Classifique 'importancia' de 1 (altíssimo impacto) a 10 (impacto praticamente nulo); "
        "eventos do mesmo relatório devem ter importâncias diferentes entre si.",
        "No campo 'impacto', explique como o evento afeta o preço do ativo, "
        "ex.: 'Indica saúde financeira, provável ascensão de preço.'.",
        "Se a seção referenciar algo incompleto ou remeter a outra parte do documento "
        "(ex.: 'conforme mencionado', 'ver nota X'), use a busca no conhecimento antes de finalizar.",
        "SEMPRE defina 'categoria' com um item exato da lista abaixo:",
        CATEGORIES_STR,
        "SEMPRE retorne SOMENTE JSON válido, no schema fornecido.",

        "# EXEMPLOS",
        "## Exemplo 1 — texto com eventos",
        "Texto: 'Durante o mês, o fundo concluiu a venda do imóvel Galpão Industrial Anhanguera "
        "por R$ 18,5 milhões, 8% acima do valor contábil. Adicionalmente, foi renegociado o "
        "contrato com o locatário Magazine Fort, com reajuste de 12% no aluguel a partir de "
        "novembro.'",
        "Saída esperada:\n"
        '{"eventos": [\n'
        '  {"titulo": "Venda de imóvel: Galpão Industrial Anhanguera", '
        '"descricao": "Fundo vendeu o imóvel por R$ 18,5 milhões, 8% acima do valor contábil.", '
        '"impacto": "Realização de ganho de capital acima do valor contábil; tende a sinalizar '
        'gestão ativa e pode impactar positivamente o preço da cota.", '
        '"importancia": 3, '
        '"categoria": "Carteira de ativos: aquisições, vendas e composição atual"},\n'
        '  {"titulo": "Renegociação de contrato: Locatário Magazine Fort", '
        '"descricao": "Reajuste de 12% no valor do aluguel a partir de novembro.", '
        '"impacto": "Aumento de receita recorrente de locação; tende a melhorar o resultado e '
        'sustentar distribuições futuras.", '
        '"importancia": 4, '
        '"categoria": "Vacância física e financeira, e negociações de locação/renovação"}\n'
        "]}",

        "## Exemplo 2 — texto sem eventos",
        "Texto: 'O fundo atua no segmento de lajes corporativas, com gestão ativa, buscando "
        "sempre maximizar a geração de valor aos cotistas. O comitê de investimentos se reuniu "
        "conforme calendário ordinário.'",
        "Saída esperada: {\"eventos\": []}",
        "Justificativa: nada acima é uma ação/decisão nova do período; é descrição estrutural "
        "do fundo e uma reunião de rotina sem consequência econômica relatada.",
        f"{PROMPT.replace("__JSON_SCHEMA__", schema_str)}"
    ]

    def __init__(self, db_path: str = "./rag_db", md_cache_dir: str = "md_cache"):
        self._db_path = db_path
        self._md_cache_dir = md_cache_dir
        self._docling_reader = None

    @property
    def reader(self) -> DoclingReader:
        if self._docling_reader is None:
            pipeline_options = PdfPipelineOptions()
            pipeline_options.do_ocr = False
            pipeline_options.do_formula_enrichment = False
            pipeline_options.generate_page_images = False
            pipeline_options.table_structure_options.mode = "FAST" # type: ignore
            pipeline_options.document_timeout = 180.0

            converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
                }
            )
            self._docling_reader = DoclingReader(converter=converter, output_format="markdown")

        return self._docling_reader

    def cache_markdown(self, url: str, ticker: str) -> str:
        ticker_upper = ticker.upper()
        target_dir = Path(self._md_cache_dir) / ticker_upper
        target_dir.mkdir(parents=True, exist_ok=True)

        period = datetime.now().strftime("%Y_%m")
        md_file_path = target_dir / f"{ticker_upper}_{period}.md"
        
        if md_file_path.exists() and md_file_path.stat().st_size > 0:
            logger.info(f"Serving cached Markdown for {ticker_upper}: {md_file_path}")
            return str(md_file_path)

        logger.info(
                f"Extracting and generating Markdown via DoclingReader for {ticker_upper} ({period}) from url: {url}"
            )        
        documents = self.reader.read(url)
        markdown_content = "\n\n".join([doc.content for doc in documents if doc.content])

        md_file_path.write_text(markdown_content, encoding="utf-8")
        logger.info(f"Successfully saved Markdown cache to: {md_file_path}")

        return str(md_file_path)

    def build_vectorstore(self, ticker: str) -> ChromaDb:
        logger.info("Building vectorstore with ChromaDB...")

        Path(self._db_path).mkdir(parents=True, exist_ok=True)

        return ChromaDb(
            collection=f"fii_{ticker.lower()}",
            name="stocks_db",
            path=self._db_path,
            search_type=SearchType.hybrid,
            embedder=OllamaEmbedder(
              id="qwen3-embedding:0.6b",
              dimensions=1024
            ),
            persistent_client=True,
        )

    def get_or_create_knowledge(self, vector_db: ChromaDb, ticker: str) -> Knowledge:
        """Create the knowledge base shared by all documents for a fund."""
        return Knowledge(
            name=f"fii_{ticker.lower()}",
            vector_db=vector_db,
            max_results=3,
        )

    def insert_to_db(self, knowledge: Knowledge, file_url: str, ticker: str) -> None:
        """Indexes a PDF (via its already-converted Markdown cache) in the vectorstore."""
        logger.info(f"Inserting file {file_url} into vectorstore...")

        md_file_path = self.cache_markdown(
            url=file_url,
            ticker=ticker,
        )

        logger.info(f"Inserting Markdown file {md_file_path} into vectorstore...")
        knowledge.insert(path=md_file_path, reader=self.reader, skip_if_exists=True, name=md_file_path)

        logger.info("File inserted successfully.")

    def extract_events_from_document(self, prompt: str, knowledge_db: Knowledge) -> EventListResponse:
        """The extraction agent runs on a entire document."""
        agent = Agent(
            role="Extrator de eventos corporativos",
            knowledge=knowledge_db,
            search_knowledge=True,
            add_knowledge_to_context=True,
            instructions=self.EXTRACTION_INSTRUCTIONS,
            model=Groq(temperature=0.1),
            debug_mode=True,
            debug_level=2
        )

        response = agent.run(prompt)
        raw_response_text = str(response.content)

        clean_json = ai_json_sanitizer(raw_response_text)
        
        return EventListResponse.model_validate_json(clean_json)

if __name__ == "__main__":
    TICKER = "MXRF11"
    service = VectorstoreService()
    db = service.build_vectorstore(TICKER)

    pdf_url = "https://fnet.bmfbovespa.com.br/fnet/publico/exibirDocumento?id=1307338&amp;cvm=true"

    knowledge = service.get_or_create_knowledge(vector_db=db, ticker=TICKER)
    service.insert_to_db(knowledge=knowledge, file_url=pdf_url, ticker=TICKER)

    events = service.extract_events_from_document(
            prompt=f"Cite ATÉ 10 eventos importantes para a cota do {TICKER}",
        knowledge_db=knowledge,
    )
    import json
    print(json.dumps(events, ensure_ascii=False, indent=4))