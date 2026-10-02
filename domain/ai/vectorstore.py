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
from pydantic import BaseModel, Field

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

    EXTRACTION_INSTRUCTIONS = [
        "Extrair ATÉ 10 eventos corporativos mais relevantes e impactantes do relatório gerencial, priorizando eventos que realmente possam afetar a percepção do investidor, os resultados da empresa ou o valor do ativo.",
        "Ignore nomes de pessoas, incluindo cargos e eleições.",
        "Preserve todos os valores numéricos, percentuais, datas, indicadores e quantias monetárias.",
        "Foque somente em movimentos, decisões, resultados e mudancas da empresa.",
        "Priorize eventos que envolvam estatísticas, números, indicadores, resultados e decisões.",
        "Os impactos também podem ser negativos.",
        "Considere relevante somente o que tiver impacto econômico concreto e atual como lucro, dívida, dividendos, expansão, risco jurídico/regulatório etc.",
        "Ignore eventos burocráticos, societários, administrativos como assembléias, reuniões, eleições, comitês, comunicados protocolares etc. ou voltados ao público como Investor Day, a menos que o texto explicite uma consequência econômica objetiva e material.",
        "NUNCA crie ou invente dados, acontecimentos.",
        "Indique nos impactos como os eventos impactaram direta ou indiretamente o preço do ativo. Ex: 'Indica saúde financeira, provável ascenção de preço.'.",
        "Classifique a importância de cada evento numa escala de 1 a 10, onde 1 = altíssimo impacto econômico e 10 = impacto praticamente nulo. Todos os eventos de uma mesmo relatório devem ter importancias diferentes entre si.",
        "Se a seção referenciar algo que parece incompleto, cortado, ou remeter a outra parte do documento (ex.: 'conforme mencionado', 'ver nota X', um valor sem sua base de comparacao), use a busca no conhecimento para complementar antes de finalizar a extração.",
        "Especifique dados concretos como nomes de empresas parceiras, nomes de produtos lançados, nomes de imóveis comprados etc. na descrição do evento.",
        "Um EVENTO válido é uma ação, decisão ou ocorrência NOVA relatada especificamente para o período coberto por este relatório -- ex.: compra ou venda de um imóvel nomeado, renegociação ou rescisão de contrato com um locatário nomeado, mudança de gestor, emissão de cotas, captação de recursos, litígio novo.",
        "NÃO é um evento: informação descritiva ou estrutural do fundo que não muda mês a mês -- ex.: 'o fundo é do segmento logístico', 'a gestão é ativa', 'o fundo investe em lajes corporativas'.",
        "Se não houver um evento adequado para preencher alguma categoria, NÃO invente um evento genérico ou descritivo só para preenchê-la. Retornar menos de 10 eventos é permitido.",
        "O TÍTULO de cada evento deve SEMPRE seguir o padrão 'Ação: Detalhe específico' -- ex.: 'Aquisição de imóvel: Shopping Park Sul', 'Renegociação de contrato: Locatário XPTO', 'Emissão de cotas: 5ª emissão, R$ 200 milhões'. NUNCA use títulos genéricos como 'Resultado do fundo' ou 'Atualização financeira'.",
        "SEMPRE retorne SOMENTE JSON válido.",
        "SEMPRE defina o campo 'categoria' com algum elemento da lista a seguir:",
        CATEGORIES_STR,
        "SEMPRE priorize 1 evento de cada categoria, isto é, evite repetir eventos de uma mesma categoria, a menos que não haja suficientes ou adequados."
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
            max_results=30,
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

    def extract_events_from_document(self, query: str, knowledge_db: Knowledge) -> list[dict]:
        """The extraction agent runs on a entire document."""
        agent = Agent(
            role="Extrator de eventos corporativos",
            knowledge=knowledge_db,
            search_knowledge=True,
            add_knowledge_to_context=True,
            instructions=self.EXTRACTION_INSTRUCTIONS,
            model=Ollama(id="qwen3:8b", options={"temperature": 0.07}),
            output_schema=EventListResponse,
            debug_mode=True,
            debug_level=2
        )

        response = agent.run(query)
        events = response.content.eventos # type: ignore

        return [event.model_dump() for event in events]

if __name__ == "__main__":
    TICKER = "MXRF11"
    service = VectorstoreService()
    db = service.build_vectorstore(TICKER)

    pdf_url = "https://fnet.bmfbovespa.com.br/fnet/publico/exibirDocumento?id=1307338&amp;cvm=true"

    knowledge = service.get_or_create_knowledge(vector_db=db, ticker=TICKER)
    service.insert_to_db(knowledge=knowledge, file_url=pdf_url, ticker=TICKER)

    events = service.extract_events_from_document(
            query=f"Cite ATÉ 10 eventos importantes para a cota do {TICKER}",
        knowledge_db=knowledge,
    )
    import json
    print(json.dumps(events, ensure_ascii=False, indent=4))