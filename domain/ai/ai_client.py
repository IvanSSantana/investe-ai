from env import AI_API_KEY
from openai import OpenAI
from agno.agent import Agent
from agno.models.ollama import Ollama
import os

os.environ["AI_API_KEY"] = AI_API_KEY
local_client = OpenAI(
    base_url='http://localhost:11434/v1/',
    api_key='ollama'
)

def local_query(persona: str, content: str, temperature: float = 0.5, max_tokens: int = 400) -> str | None:
    """
    Wrapper for local AI calls.
    """

    local_agent = Agent(
        model=Ollama(
            id="qwen2.5:7b",
            options={
                "temperature": temperature,
                "num_predict": max_tokens
            },
        ),
        instructions=persona,
        markdown=False
    )

    response = local_agent.run(content)
    return response.content