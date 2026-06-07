"""
Utils package - Shared utilities for LLM calls, JSON parsing, and cost tracking.

Migration: LLM calls now use LangChain's ChatGoogleGenerativeAI.
get_llm() returns a LangChain model instance for use in chains.
"""
from utils.llm_client import (
    get_llm,
    call_llm,
    call_llm_json,
    safe_parse_json,
    truncate_for_llm,
    track_cost,
)

__all__ = [
    "get_llm",
    "call_llm",
    "call_llm_json",
    "safe_parse_json",
    "truncate_for_llm",
    "track_cost",
]
