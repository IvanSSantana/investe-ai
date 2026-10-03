PROMPT = """
    [REGRA CRÍTICA DE FORMATO DE SAÍDA - LEIA COM ATENÇÃO]
    Você deve responder EXCLUSIVAMENTE com um objeto JSON válido que siga a estrutura abaixo.

    REGRAS OBRIGATÓRIAS DE FORMATAÇÃO:
    1. Responda APENAS com o JSON. NÃO inclua nenhum texto explicativo, saudações, introduções ou notas.
    2. É PROIBIDO utilizar blocos de código Markdown (NÃO inclua ```json ou ```).
    3. Inicie sua resposta estritamente com o caractere '{' e termine com '}'.
    4. Para campos numéricos/monetários, utilize apenas números em formato float (ex: 102.50). NUNCA inclua "R$", "%", vírgulas como separadores decimais ou aspas em valores numéricos.

    ESQUEMA JSON OBRIGATÓRIO:
    {json_schema}
"""
