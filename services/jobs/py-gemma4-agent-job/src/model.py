import os
from functools import lru_cache

from langchain_openai import ChatOpenAI


@lru_cache(maxsize=1)
def get_chat_model() -> ChatOpenAI:
    """Cria o cliente LangChain para a API local compatível com OpenAI."""
    return ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gemma4"),
        base_url=os.getenv("OPENAI_BASE_URL", "http://10.247.168.43:8072/v1"),
        api_key=os.getenv("OPENAI_API_KEY", "EMPTY"),
        temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.2")),
        max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "1024")),
        timeout=float(os.getenv("OPENAI_TIMEOUT_SECONDS", "120")),
        max_retries=int(os.getenv("OPENAI_MAX_RETRIES", "2")),
    )
