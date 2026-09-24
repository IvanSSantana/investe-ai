# Investe Aí - Automação de Análise de Fundos Imobiliários (FIIs)

O **Investe Aí** é uma API REST desenvolvida em Python com o framework **FastAPI**, projetada para automatizar a coleta de dados, extração de indicadores fundamentalistas e sumarização de relatórios gerenciais de Fundos de Investimento Imobiliário (FIIs) com envio automatizado via e-mail.

O projeto utiliza modelos **Ollama** combinado com técnicas de RAG (*Retrieval-Augmented Generation*) sobre os arquivos PDF dos relatórios gerenciais, sendo projetado para execução no **Google Colab** ou em ambientes locais.

---

## 🏛️ Estrutura do Projeto e Arquitetura

A estrutura de arquivos do projeto reflete a separação em camadas de aplicação, domínio, comunicação e infraestrutura:

```text
investe-ai/
├── api/
│   ├── main.py                          # Ponto de entrada e inicialização da API FastAPI
│   └── routers/
│       └── fii.py                       # Rotas e endpoints REST para operações com FIIs
├── application/
│   └── use_cases/
│       ├── generate_report_fii.py       # Caso de uso: Orquestração e geração do relatório completo
│       └── get_indicators_fii.py        # Caso de uso: Coleta e estruturação de indicadores
├── communication/
│   ├── dtos.py                          # Data Transfer Objects (Pydantic models)
│   └── exceptions.py                    # Tratamento de exceções personalizadas da API
├── domain/
│   ├── ai/
│   │   ├── ai_client.py                 # Conectores e configuração do cliente Gemini API
│   │   ├── ai_service.py                # Interface de geração de análises e prompts
│   │   ├── chunking.py                  # Fatiamento e segmentação de texto dos PDFs
│   │   └── vectorstore.py               # Indexação e busca por similaridade vetorial (RAG)
│   ├── files/
│   │   ├── indicator_interpreter.py     # Interpretação qualitativa das métricas coletadas
│   │   ├── pdf_downloader.py            # Download dos relatórios gerenciais em formato PDF
│   │   ├── report_builder.py            # Montagem e renderização do relatório final
│   │   └── templates/
│   │       └── report_fii.md            # Template