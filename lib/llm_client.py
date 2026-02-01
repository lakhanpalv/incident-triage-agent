from openai import AzureOpenAI
import os

def get_client():
    """Lazy-load the OpenAI client to ensure environment variables are loaded"""
    return AzureOpenAI(
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
    )

def call_llm(messages, temperature: float = 0.7, max_tokens: int = 1000) -> str:
    client = get_client()
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    response = client.chat.completions.create(
        model=deployment,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens
    )
    return response.choices[0].message.content