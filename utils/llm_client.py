"""
Shared LLM Client - Central wrapper for all LLM calls using LangChain.
All agents should use this instead of calling LLMs directly.

Migration: Replaced raw `google.genai` SDK with LangChain's ChatGoogleGenerativeAI.
Public API (call_llm, call_llm_json, safe_parse_json, truncate_for_llm) is preserved.
"""
import time
import json
import re
import os
import sys
from typing import Optional, Dict, Any, List

# Reconfigure stdout/stderr to UTF-8 to prevent UnicodeEncodeError with emojis on Windows console
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()

# Subclass ChatOpenAI to provide compatibility with response_mime_type parameter
# commonly used in older Gemini configurations, mapping it to response_format
class PatchedChatOpenAI(ChatOpenAI):
    def bind(self, *args, **kwargs):
        if "response_mime_type" in kwargs:
            val = kwargs.pop("response_mime_type")
            if val == "application/json":
                kwargs["response_format"] = {"type": "json_object"}
        return super().bind(*args, **kwargs)

# Map Gemini models to OpenAI counterparts for backward compatibility
MODEL_MAPPING = {
    "gemini-2.0-flash": "gpt-4o-mini",
    "gemini-1.5-flash": "gpt-4o-mini",
    "gemini-2.0-pro": "gpt-4o",
}

# ── Pricing (per token) ────────────────────────────────────────────
PRICING = {
    "gpt-4o-mini": {"input": 0.150 / 1_000_000, "output": 0.600 / 1_000_000},
    "gpt-4o":   {"input": 2.50 / 1_000_000, "output": 10.0 / 1_000_000},
    "gemini-2.0-flash": {"input": 0.150 / 1_000_000, "output": 0.600 / 1_000_000},
    "gemini-2.0-pro":   {"input": 2.50 / 1_000_000, "output": 10.0 / 1_000_000},
    "gemini-1.5-flash":  {"input": 0.150 / 1_000_000, "output": 0.600 / 1_000_000},
}


# ── LangChain LLM Factory ────────────────────────────────────────
def get_llm(
    model: str = "gemini-2.0-flash",
    temperature: float = 0.3,
    max_retries: int = 5,
) -> ChatOpenAI:
    """
    Get a LangChain ChatOpenAI model instance (custom patched for compatibility).
    
    This is the primary way to get an LLM for use in LangChain chains.
    All calls through this model are automatically traced by LangSmith
    when LANGCHAIN_TRACING_V2=true is set in the environment.
    
    Args:
        model: Model name (default: gemini-2.0-flash, mapped to gpt-4o-mini)
        temperature: Sampling temperature
        max_retries: Number of retries on failure (handled by LangChain)
    
    Returns:
        PatchedChatOpenAI instance
    """
    # Map model if present in MODEL_MAPPING, otherwise use it directly
    openai_model = MODEL_MAPPING.get(model, model)
    if "gemini" in openai_model:
        openai_model = "gpt-4o-mini"
        
    # # commented out google genai code:
    # api_key = os.getenv("GEMINI_API_KEY")
    # if not api_key:
    #     raise ValueError("GEMINI_API_KEY not found in environment variables")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")
    
    return PatchedChatOpenAI(
        model=openai_model,
        temperature=temperature,
        max_retries=max_retries,
        api_key=api_key,
    )


# ── Core LLM call with retry (backward-compatible API) ───────────
def call_llm(
    messages: List[Dict[str, str]],
    model: str = "gemini-2.0-flash",
    temperature: float = 0.3,
    max_retries: int = 5,
    json_mode: bool = False,
) -> str:
    """
    Call OpenAI via LangChain with automatic retry on rate-limits and API errors.
    
    This function maintains the same signature as the original raw-SDK version
    so all existing agent code continues to work unchanged during migration.
    
    Args:
        messages: Chat messages list (OpenAI-style: role/content dicts)
        model: Model name (default: gemini-2.0-flash, mapped to gpt-4o-mini)
        temperature: Sampling temperature
        max_retries: Number of retries on failure
        json_mode: If True, request JSON output
    
    Returns:
        The LLM response content string
    """
    try:
        llm = get_llm(model=model, temperature=temperature, max_retries=max_retries)
        
        # Convert OpenAI-style messages to LangChain message objects
        lc_messages = _convert_messages(messages)
        
        # Use JSON mode if requested
        if json_mode:
            llm = llm.bind(response_format={"type": "json_object"})
        
        # Invoke the model (LangChain handles retries internally)
        response = llm.invoke(lc_messages)
        return response.content
        
    except Exception as e:
        print(f"  ❌ LLM call failed: {e}")
        fallback = "LLM unavailable after retries"
        if json_mode:
            return json.dumps({"error": fallback, "summary": "Unable to process"})
        return fallback


def call_llm_json(
    messages: List[Dict[str, str]],
    model: str = "gemini-2.0-flash",
    temperature: float = 0.3,
    fallback: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Call Gemini via LangChain and parse the response as JSON with triple-layer safety.
    
    Returns:
        Parsed dict — never raises, always returns a dict
    """
    raw = call_llm(messages, model=model, temperature=temperature, json_mode=True)
    return safe_parse_json(raw, fallback=fallback)


# ── Helper: Convert OpenAI-style messages to LangChain ────────────
def _convert_messages(messages: List[Dict[str, str]]) -> list:
    """
    Convert OpenAI-style message dicts to LangChain message objects.
    
    Supports: system, user, assistant roles.
    """
    lc_messages = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        
        if role == "system":
            lc_messages.append(SystemMessage(content=content))
        elif role == "assistant":
            from langchain_core.messages import AIMessage
            lc_messages.append(AIMessage(content=content))
        else:  # "user"
            lc_messages.append(HumanMessage(content=content))
    
    return lc_messages


# ── JSON Safety Parser (unchanged) ───────────────────────────────
def safe_parse_json(text: str, fallback: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Triple-layer JSON parser:
    1. Direct parse
    2. Extract from ```json``` code blocks
    3. Find any {...} in the text
    Falls back to a safe dict on complete failure.
    """
    # Layer 1: Direct parse
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass
    
    # Layer 2: Extract from markdown code blocks
    if text:
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Layer 3: Find any {...} block
        brace_match = re.search(r'\{[\s\S]*\}', text)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass
    
    print(f"  ⚠️ JSON parse failed. Raw: {str(text)[:200]}")
    return fallback or {"error": "Failed to parse LLM output", "raw": str(text)[:500]}


# ── Cost Tracking (unchanged) ─────────────────────────────────────
def track_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Calculate cost in USD for a single LLM call."""
    rates = PRICING.get(model, PRICING["gemini-2.0-flash"])
    cost = (prompt_tokens * rates["input"]) + (completion_tokens * rates["output"])
    return round(cost, 6)


def truncate_for_llm(text: str, max_chars: int = 8000) -> str:
    """
    Truncate text for LLM input to manage costs.
    Keeps first and last portions (intro + conclusion are most valuable).
    """
    if len(text) <= max_chars:
        return text
    half = max_chars // 2
    return text[:half] + "\n\n[... content truncated ...]\n\n" + text[-half:]
