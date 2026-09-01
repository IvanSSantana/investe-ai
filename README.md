# Investe Aí

Projeto de **scraping, processamento de PDFs e análise de eventos financeiros com IA**, desenvolvido para identificar informações relevantes em relatórios gerenciais e comunicados de fundos imobiliários e ações da bolsa de valores brasileira (B3).

O projeto utiliza **RAG (Retrieval-Augmented Generation)** para fornecer ao modelo de IA informações extraídas dos documentos antes da análise, com uma abordagem **agentic**: o próprio agente decide quando consultar a base de conhecimento, em vez de a busca ser sempre forçada antes de cada resposta.

## Tecnologias

* Python
* Selenium / BeautifulSoup (scraping)
* Docling (leitura e estruturação de PDFs) — chunking já integrado; leitura do PDF em si ainda não
* Agno (agentes de IA)
* ChromaDB (banco vetorial)
* Ollama — modelos locais: `qwen3:8b` (extração de eventos) e `qwen2.5:7b` (chamadas simples)
* `nomic-embed-text` (embedding, via Ollama)
* Semantic Chunking / Hybrid Chunking
* Pydantic

## Arquitetura pretendida

O fluxo que o projeto foi desenhado para ter, de ponta a ponta:

```text
Site (investidor10.com)
  ↓
Scraping dos indicadores e dos links de comunicados       (implementado)
  ↓
Download dos PDFs
  ↓
Leitura do documento (Docling)                            (não implementado)
  ↓
Divisão por seção (chunking grosso)                       (configurado, função não escrita)
  │
  ├─→ Chunks finos + embeddings ──→ ChromaDB               (implementado)
  │
  Para cada seção: ────────────────┘
  ↓
Agente de IA extrai os eventos da seção                    (implementado, função isolada)
  │
  ├─→ Contexto da seção suficiente: extrai direto
  └─→ Contexto insuficiente: busca complementar no ChromaDB (agentic RAG)
  ↓
Eventos corporativos filtrados por relevância               (não implementado)
  ↓
Geração da conclusão e do relatório final (Markdown)         (não implementado)
```

O agente analisa o conteúdo de uma seção do documento e identifica os eventos mais relevantes para o ativo, considerando fatores que podem impactar diretamente o preço. A busca no banco vetorial é pensada como complemento pontual (quando a seção referencia algo incompleto ou remete a outra parte do documento), não como único mecanismo de busca.

## RAG

Os documentos são indexados no **ChromaDB** em chunks semânticos finos (`SemanticChunking`), com embeddings gerados via `nomic-embed-text` (Ollama, 768 dimensões) — 100% local, sem dependência de API de embedding externa.

A busca é feita de forma **agentic RAG**: o agente extrator recebe a ferramenta de busca no ChromaDB (`search_knowledge=True`), mas decide por conta própria se e quando consultá-la — a busca não é forçada antes de cada resposta, como seria num RAG comum.

O plano é combinar isso com **chunking grosso por seção** (via `HybridChunker`, respeitando a estrutura extraída pelo Docling) para a extração exaustiva de eventos — um chunk por seção, evitando tanto perder eventos quanto estourar o contexto do modelo com o documento inteiro de uma vez. Essa integração ainda não está montada (ver Status).

## Estrutura

```text
.
├── domain/
│   ├── ai/                # ai_client.py, chunking.py, vectorstore.py
│   ├── scraping/           # scraping_service.py, searching.py
│   └── files/               # (vazio — leitura de PDF ainda não implementada)
├── communication/
│   ├── dtos.py
│   └── exceptions.py
├── helpers/
│   └── typing/              # price_sanitizer.py
├── api/                      # (vazio)
├── application/              # (vazio)
├── repository/                # (vazio)
├── tests/                      # (vazio)
└── README.md
```

> A estrutura pode variar conforme a evolução do projeto.

## Rodar o projeto

Ao fim do projeto disponibilizarei um projeto Colab pré-configurado para rodar o sistema.

## Objetivo

O projeto tem como objetivo **automatizar a leitura e análise de documentos financeiros**, transformando relatórios extensos em informações estruturadas que possam auxiliar na análise de ativos — tanto de forma retroativa (o que já aconteceu com a empresa) quanto, futuramente, preditiva (com base no histórico acumulado de documentos analisados).

## Status

Em desenvolvimento.

**Implementado:**
- Scraping de indicadores fundamentalistas e links de comunicados (`ScrapingService`)
- Indexação de PDFs no ChromaDB com embeddings locais (`VectorstoreService.insert_to_db`)
- Extração agentic RAG de eventos a partir de um texto/seção (`VectorstoreService.extract_events_from_section`)

**Em construção:**
- Leitura de PDF via Docling (`domain/files/`)
- Divisão do documento em seções (`chunk_by_section`, hoje só configurado, não escrito)
- Orquestração ponta a ponta (ler PDF → dividir em seções → extrair eventos de cada uma → filtrar por importância → gerar conclusão)
- Camadas de API, aplicação e persistência (`api/`, `application/`, `repository/`)
- Relatório preditivo, baseado no histórico acumulado de documentos indexados
- Exportação de CSV para múltiplos ativos
- Suporte completo a fundos imobiliários (scraping ainda cobre majoritariamente ações)
