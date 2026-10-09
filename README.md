# Investe Aí

API em Python para análise fundamentalista automatizada de Fundos de Investimento Imobiliário (FIIs) da B3, combinando web scraping, um pipeline de agentes de IA (RAG + LLM) e geração de relatórios.

## Objetivo

Dado um ticker de FII, a API:

1. Coleta indicadores fundamentalistas e o relatório gerencial mais recente do fundo via scraping do [investidor10.com.br](https://investidor10.com.br).
2. Extrai, via um agente de IA com RAG sobre o PDF do relatório, os eventos corporativos relevantes do período (aquisições, renegociações de contrato, mudanças de gestão, etc.).
3. Gera uma conclusão textual cruzando esses eventos com contexto de mercado (preço, notícias, recomendações de analistas).
4. Produz valuation quantitativo (DDM, reversão à média do P/VP) e uma previsão qualitativa de curto (30 dias) e médio prazo (12 meses) assinada por um agente de IA.
5. Entrega tudo isso como relatório Markdown, JSON estruturado ou CSV histórico — sob demanda, por e-mail, ou em agendamento mensal recorrente.

Projetado para rodar tanto localmente quanto no Google Colab (o driver de scraping depende de `google_colab_selenium`).

## Arquitetura

O projeto segue separação em camadas inspirada em Clean Architecture, sem framework de DI — a injeção de dependências é feita por valores-padrão nos construtores (`def __init__(self, service: Service = Service())`).

```text
investe-ai/
├── api/
│   ├── main.py                        # Configuração do FastAPI, registro de routers, exception handlers
│   ├── dependencies/
│   │   └── auth.py                    # Dependencies de autenticação (API key de cliente e chave de admin)
│   └── routers/
│       ├── fii_public.py              # Rotas sem autenticação (indicators, history/csv)
│       ├── fii.py                     # Rotas protegidas por API key (report, send-email, schedule-email, valuation-prediction)
│       └── auth.py                    # Rotas de gerenciamento de chaves, protegidas por chave de admin
├── application/
│   └── use_cases/                     # Orquestração: um caso de uso por operação de negócio
│       ├── get_indicators_fii.py
│       ├── generate_report_fii.py
│       ├── predict_valuation_fii.py
│       ├── export_price_history_fii.py
│       └── send_email_report.py
├── domain/
│   ├── ai/                            # Agentes Agno (extração de eventos, conclusão, valuation, explicação de variação)
│   ├── files/                         # Construção de relatório, cálculo de valuation, resolução de URL, export CSV
│   └── scraping/                      # Scraping do investidor10.com.br (requests + Selenium)
├── communication/
│   ├── dtos.py                        # Modelos Pydantic de entrada/saída da API
│   └── exceptions.py                  # Exceções de domínio, mapeadas a HTTP status na camada api
├── infrastructure/                    # Integrações externas: e-mail, yfinance, Banco Central, agendador
├── repository/                        # Persistência simples em arquivo/SQLite (registry de relatórios, chaves de API)
└── helpers/                           # Funções puras reutilizáveis (sanitização, formatação, prompts, geração de chaves)
```

### Fluxo de uma predição de valuation (`GET /{ticker}/valuation-prediction`)

```
ScrapingService + YFinanceService + MarketDataService  →  indicadores atuais, histórico de dividendos, Selic
                            ↓
                  ValuationCalculator (determinístico: DDM, reversão P/VP, spread de yield)
                            ↓
          VectorstoreService (ChromaDB + Docling)  →  RAG sobre o relatório gerencial em PDF
                            ↓
                   ValuationAgent (Groq)  →  síntese final: tendências, faixa de preço justo, sinal de recomendação
                            ↓
                 cache mensal em JSON (prediction_cache/)
```

A âncora numérica (DDM, reversão de P/VP) é sempre calculada deterministicamente em `ValuationCalculator` — o LLM nunca inventa esses números, apenas os interpreta e contextualiza.

## Decisões técnicas e trade-offs

### Scraping híbrido: `requests`+`BeautifulSoup` vs. Selenium

A maior parte das páginas do investidor10 é extraída com `requests`/`BeautifulSoup` (rápido, sem overhead de browser). Mas a tabela histórica de indicadores e o gráfico de variação de preço são renderizados via JavaScript, exigindo Selenium com espera explícita (`WebDriverWait`).

- **Trade-off:** Selenium é ordens de magnitude mais lento e mais frágil (depende de seletores CSS que quebram com qualquer mudança no front-end do site) que uma chamada HTTP simples. A escolha foi usá-lo só onde é estritamente necessário (dados client-side), mantendo o restante em `requests` puro.
- Cada chamada que usa Selenium abre e fecha um driver novo (`driver.quit()` em `finally`) — não há reuso de sessão entre indicadores. Isso é mais custoso, mas evita estado compartilhado e vazamento de processos de browser entre chamadas concorrentes da API.

### `Decimal` em vez de `float` em todo o domínio financeiro

Todos os valores monetários e percentuais (preços, P/VP, dividendos, taxas) trafegam como `Decimal`, não `float`, do scraping até a resposta da API.

- **Trade-off:** `Decimal` é mais verboso (requer conversões explícitas, não tem suporte nativo a todas operações que `float` tem) e marginalmente mais lento. Mas evita erros de arredondamento de ponto flutuante binário em cálculos financeiros encadeados (ex.: `0.1 + 0.2 != 0.3` em `float`), que seriam inaceitáveis em valores exibidos a investidores.

### Cache em arquivo (JSON/CSV) em múltiplas camadas, sem banco de dados central

- `indicators_cache/`: diário, por ticker.
- `md_cache/`: Markdown já convertido do PDF (evita reprocessar o mesmo relatório via Docling).
- `csv_cache/`: mensal, separado por `include_explanation` (`_explained` vs `_raw`).
- `prediction_cache/`: mensal, por ticker.
- `reports_db/registry.json`: índice de qual PDF gerou o último relatório de cada ticker (evita regenerar se a fonte não mudou).

- **Trade-off:** sem banco de dados, não há consultas relacionais, concorrência seguro-contra-corrida garantida, nem invalidação centralizada — cada cache gerencia sua própria expiração e purga (`_purge_old_caches`) de forma independente e um pouco duplicada entre use cases. A vantagem é zero infraestrutura extra: o projeto roda com um `pip install` e um diretório gravável, o que importa para o caso de uso em Google Colab (sem servidor de banco disponível).
- Ao introduzir autenticação, a chave de API quebrou esse padrão deliberadamente: **SQLite**, não JSON, é usado em `repository/api_key_repository.py` (ver seção seguinte).

### Migração para SQLite only para API keys

Diferente dos outros caches (arquivo por ticker/mês), chaves de API exigem busca por igualdade exata (lookup por hash em toda requisição autenticada), unicidade garantida e updates atômicos (revogação). Um `registry.json` serviria, mas exigiria reimplementar manualmente índice, unicidade e concorrência de escrita — exatamente o que um banco relacional já resolve.

- **Trade-off:** introduz a primeira dependência de banco do projeto (`sqlite3`, stdlib — sem novo pacote). Escolhido em vez de PostgreSQL/outro SGBD por não exigir infraestrutura externa, mantendo a filosofia "roda com um diretório gravável" do resto do projeto.

### Autenticação: API Key com escopo por router, não OAuth2/JWT

Decisão explícita de usar chaves de API opacas (`inv_<token_urlsafe(32)>`) em vez de OAuth2 Password + JWT. O caso de uso é uma API consumida por integrações/scripts, não por usuários finais fazendo login interativo — não há necessidade do conceito de "sessão de usuário" que OAuth2 Password introduziria.

- **Modelo de dados:** `key_id` (UUID público, usado para listar/revogar), `key_hash` (SHA-256 do plaintext, nunca o plaintext em si, usado só para validar requisições), `name` (rótulo humano), `created_at`/`expires_at` (expiração opcional e automática) e `active` (revogação manual e imediata, independente de expiração — permite invalidar uma chave vazada sem esperar sua data de expiração, e sem apagar o registro para fins de auditoria).
- **Trade-off:** sem refresh tokens, sem granularidade de permissões por chave (é tudo-ou-nada por rota), sem múltiplos "usuários" — adequado ao escopo atual (uma aplicação, poucas integrações), mas exigiria retrabalho se o projeto crescesse para múltiplos tenants com permissões diferenciadas.
- **Escopo por router, não por endpoint individual:** `fii_public.py` (sem autenticação: `indicators`, `history/csv`), `fii.py` (API key obrigatória: `report`, `send-email`, `schedule-email`, `valuation-prediction` — todas as rotas que disparam o pipeline de IA), `auth.py` (chave de admin via `ADMIN_API_KEY`, para gerar/revogar chaves). A proteção é uma `dependency` no nível do `APIRouter`, não decorators por função — novas rotas adicionadas a um desses routers herdam a proteção automaticamente, sem risco de esquecer de proteger uma rota nova.
- **Degradação graciosa em `history/csv`:** a rota permanece pública mesmo com o parâmetro `include_explanation=True`, mas a explicação gerada por IA só é produzida se uma API key válida for enviada (`optional_api_key`, que nunca lança 401, apenas retorna um booleano). Sem chave, o CSV ainda é servido, só que sem o enriquecimento de IA — evita que a rota pública consuma o pipeline de IA sem controle de acesso, sem bloquear o uso básico do dado público.

### Groq em vez de Ollama local para os agentes de IA

Todos os 4 agentes (`ConclusionAgent`, `ValuationAgent`, extração de eventos em `VectorstoreService`, `VariationExplainAgent`) rodam sobre `Groq`. Os imports de `Ollama` permanecem no código (não removidos) mas não são instanciados.

- **Trade-off:** depende de API externa (latência de rede, rate limits, custo por chamada) em vez de inferência local gratuita. Em contrapartida, modelos hospedados na Groq são maiores e mais capazes que os modelos locais viáveis (`qwen3:8b`), e a infraestrutura de Google Colab não garante GPU persistente nem dedicada para servir um modelo local com latência aceitável.
- Como a Groq (via API genérica de chat) não oferece o mesmo mecanismo de `output_schema` nativo que a integração Ollama do Agno expunha, os agentes passaram a instruir o JSON esperado via prompt (`helpers/ai/json_prompt.py`, com um schema explícito injetado no texto) e fazer o parsing manual da resposta: `ai_json_sanitizer()` remove cercas Markdown e extrai o bloco `{...}` via regex, e só então o texto é validado contra o schema Pydantic (`Model.model_validate_json`). Essa camada de sanitização é necessária justamente porque o modelo às vezes insere texto ou formatação ao redor do JSON, mesmo quando instruído a não fazer isso.

### RAG com ChromaDB + Docling, escopado por fundo

Cada ticker tem sua própria collection no ChromaDB (`fii_{ticker.lower()}`), com embeddings Ollama (`qwen3-embedding:0.6b`) e busca híbrida (`SearchType.hybrid`). O PDF do relatório gerencial é convertido para Markdown via Docling (OCR desabilitado, parsing de tabela em modo `FAST`) e cacheado em disco antes da indexação, para não reprocessar o mesmo PDF em execuções futuras.

- **Trade-off:** escopar por fundo evita contaminação cruzada entre tickers na busca vetorial, mas também significa que não há conhecimento compartilhado entre fundos (cada collection é isolada). `max_results=3` na busca de conhecimento foi reduzido deliberadamente de um valor maior para conter o volume de tokens enviado ao modelo por chamada, já que a Groq aplica rate limit por tokens-por-minuto — o trade-off direto é menos contexto recuperado por consulta.

### Prompt estruturado e few-shot para extração de eventos

O prompt de extração de eventos (`EXTRACTION_INSTRUCTIONS` em `vectorstore.py`) é organizado em seções curtas (`# PAPEL`, `# O QUE É UM EVENTO`, `# O QUE NÃO É UM EVENTO`, `# FORMATO DO TÍTULO`, `# REGRA MAIS IMPORTANTE`) com dois exemplos few-shot (um com eventos, um sem), e uma regra explícita de que retornar uma lista vazia é preferível a inventar um evento genérico.

- **Trade-off:** prompt mais longo consome mais tokens por chamada, mas modelos menores (como os disponíveis gratuitamente via Groq) são mais propensos a alucinar ou a extrair informação genérica sem essa estrutura e exemplos explícitos — o custo em tokens foi aceito em troca de maior fidelidade factual do conteúdo extraído, que alimenta diretamente o relatório final entregue ao investidor.

### Agendamento de envio recorrente via APScheduler

`schedule-email` usa `AsyncIOScheduler` com `CronTrigger` fixado em `America/Sao_Paulo`, mantendo os jobs em memória (não persistidos em banco).

- **Trade-off:** jobs agendados são perdidos se o processo da API reiniciar — não há persistência de agendamentos entre deploys. Aceitável dado o escopo atual (uso pessoal/pequena escala), mas seria um ponto a revisar para um cenário de produção com múltiplas instâncias ou necessidade de alta disponibilidade dos agendamentos.

## Autenticação

| Rota | Autenticação |
|---|---|
| `GET /{ticker}/indicators` | Pública |
| `GET /{ticker}/history/csv` | Pública (explicação de IA exige `X-API-Key` válida; sem ela, `include_explanation` é forçado a `False`) |
| `GET /{ticker}/report` | `X-API-Key` |
| `POST /send-email` | `X-API-Key` |
| `POST /schedule-email` | `X-API-Key` |
| `GET /{ticker}/valuation-prediction` | `X-API-Key` |
| `POST /api/v1/auth/keys` | `X-Admin-Key` (`ADMIN_API_KEY` no `.env`) |
| `DELETE /api/v1/auth/keys/{key_id}` | `X-Admin-Key` |

Chaves de API são opacas (`inv_<32 bytes aleatórios>`), armazenadas apenas como hash SHA-256 em SQLite (`auth_db/api_keys.db`), nunca em texto plano. A revogação é soft-delete (`active=False`) — o registro é preservado para auditoria.
