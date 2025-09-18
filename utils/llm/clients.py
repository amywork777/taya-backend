import os
from typing import List

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.caches import BaseCache  # ensure forward ref exists
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

# Ensure Pydantic models are fully built for newer Pydantic versions
try:
    ChatOpenAI.model_rebuild()
except Exception:
    pass
try:
    OpenAIEmbeddings.model_rebuild()
except Exception:
    pass
import tiktoken

from models.conversation import Structured


def _make_llm(**kwargs):
    # Avoid model initialization failures during import time; let errors surface at first use
    return ChatOpenAI(**kwargs)

llm_mini = _make_llm(model='gpt-4o-mini')
llm_mini_stream = _make_llm(model='gpt-4o-mini', streaming=True)
llm_large = _make_llm(model='o1-preview')
llm_large_stream = _make_llm(model='o1-preview', streaming=True, temperature=1)
llm_high = _make_llm(model='o4-mini')
llm_high_stream = _make_llm(model='o4-mini', streaming=True, temperature=1)
llm_medium = _make_llm(model='gpt-4o')
llm_medium_experiment = _make_llm(model='gpt-4.1')
llm_medium_stream = _make_llm(model='gpt-4o', streaming=True)
llm_persona_mini_stream = ChatOpenAI(
    temperature=0.8,
    model="google/gemini-flash-1.5-8b",
    api_key=os.environ.get('OPENROUTER_API_KEY'),
    base_url="https://openrouter.ai/api/v1",
    default_headers={"X-Title": "Omi Chat"},
    streaming=True,
)
llm_persona_medium_stream = ChatOpenAI(
    temperature=0.8,
    model="anthropic/claude-3.5-sonnet",
    api_key=os.environ.get('OPENROUTER_API_KEY'),
    base_url="https://openrouter.ai/api/v1",
    default_headers={"X-Title": "Omi Chat"},
    streaming=True,
)
embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
parser = PydanticOutputParser(pydantic_object=Structured)

encoding = tiktoken.encoding_for_model('gpt-4')


def num_tokens_from_string(string: str) -> int:
    """Returns the number of tokens in a text string."""
    num_tokens = len(encoding.encode(string))
    return num_tokens


def generate_embedding(content: str) -> List[float]:
    return embeddings.embed_documents([content])[0]
