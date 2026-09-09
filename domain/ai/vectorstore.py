import logging
from pathlib import Path

from agno.vectordb.chroma import ChromaDb, SearchType
from agno.knowledge import Knowledge
from agno.knowledge.chunking.semantic import SemanticChunking
from agno.knowledge.embedder.ollama import OllamaEmbedder
from agno.knowledge.reader.pdf_reader import PDFReader

from agno.agent import Agent
from agno.models.ollama import Ollama
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class EventResponse(BaseModel):
    titulo: str = Field(..., description="Titulo do evento corporativo extraido do documento.")
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

    # NOTE: Problem with importancy. It's necessary to specify criteria for rate importance.
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
        "SEMPRE retorne SOMENTE JSON válido.",
        "SEMPRE defina o campo 'categoria' com algum elemento da lista a seguir:",
        CATEGORIES_STR,
        "SEMPRE priorize 1 evento de cada categoria, isto é, evite repetir eventos de uma mesma categoria, a menos que não haja suficientes ou adequados."
    ]

    def __init__(self, db_path: str = "./rag_db"):
        self._db_path = db_path

    def build_vectorstore(self) -> ChromaDb:
        logger.info("Building vectorstore with ChromaDB...")

        Path(self._db_path).mkdir(parents=True, exist_ok=True)

        return ChromaDb (
            collection="stocks_collection",
            name="stocks_db",
            path=self._db_path,
            search_type=SearchType.hybrid,
            embedder=OllamaEmbedder(
              id="nomic-embed-text",
              dimensions=768
            ),
            persistent_client=True,
        )

    def insert_to_db(self, vector_db: ChromaDb, file_path: str) -> Knowledge:
        """Indexes a PDF in the vectorstore in granular chunks."""
        logger.info(f"Inserting file {file_path} into vectorstore...")

        knowledge = Knowledge(name=file_path, vector_db=vector_db, max_results=25)

        # TODO: Change Reader to Docling
        reader = PDFReader(chunking_strategy=SemanticChunking(chunk_size=1000, embedder=vector_db.embedder))
        knowledge.insert(path=file_path, reader=reader, skip_if_exists=True, name=file_path)

        logger.info("File inserted successfully.")
        return knowledge

    def extract_events_from_section(self, section: str, knowledge_db: Knowledge) -> list[dict]:
        """The extraction agent runs on a section of the document. The agent decides
        on its own (agentic RAG) whether it needs to consult the indexed
        knowledge to supplement incomplete context.
        """
        agent = Agent(
            role="Extrator de eventos corporativos",
            knowledge=knowledge_db,
            search_knowledge=True, 
            instructions=self.EXTRACTION_INSTRUCTIONS,
            model=Ollama(id="qwen3:8b", options={"temperature": 0.04}),
            output_schema=EventListResponse,
            debug_mode=True,
            debug_level=2
        )

        response = agent.run(section)
        events = response.content.eventos # type: ignore

        return [event.model_dump() for event in events]

if __name__ == "__main__":
    service = VectorstoreService()
    db = service.build_vectorstore()

    pdf_path = "Relatório Gerencial MXRF11.pdf"

    knowledge = service.insert_to_db(vector_db=db, file_path=pdf_path)
    
    events = service.extract_events_from_section(
        section=f"Quais sao os eventos mais relevantes e impactantes para o fundo MXRF11? Indique os impactos diretos ao preco da acao. Busque os eventos mais relevantes com base em cada categoria a seguir: {CATEGORIES_STR}.",
        knowledge_db=knowledge,
    )
    import json
    print(json.dumps(events, ensure_ascii=False, indent=4))