from openai import OpenAI
from agno.agent import Agent
from agno.models.ollama import Ollama
import os

local_client = OpenAI(
    base_url='http://localhost:11434/v1/',
    api_key='ollama'
)

def local_query(
    persona: str,
    content: str,
    temperature: float = 0.5,
    max_tokens: int = 400,
) -> str | None:
    """Executes a query against a local AI model using a defined persona.

    Args:
        persona (str): Instructions that define the AI's role, behavior, and response style.
        content (str): The prompt or content to be processed by the model.
        temperature (float): Controls the randomness of the model's responses. 
            Lower values produce more deterministic outputs, while higher values allow greater variation.
        max_tokens (int): Maximum number of tokens the model may generate in the response.

    Returns:
        str | None: The model's response content, or None if no content is returned.
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