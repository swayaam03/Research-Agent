# ============================================
# AI Research Agent - LLM Service
# ============================================
"""
LLM initialization and configuration using OpenRouter.

ARCHITECTURE DECISION: WHY A SEPARATE LLM SERVICE?
---------------------------------------------------
Instead of creating ChatOpenAI() instances scattered throughout nodes,
we centralize LLM creation here. This gives us:

1. Single Point of Change: Switch from OpenRouter to direct Gemini API?
   Change ONE file, not every node.

2. Consistent Configuration: Every node gets the same temperature, model,
   and API settings. No accidental mismatches.

3. Testability: In tests, we can mock get_llm() to return a fake LLM
   without touching any node code.

HOW OPENROUTER WORKS WITH LANGCHAIN:
------------------------------------
OpenRouter exposes an OpenAI-compatible API at https://openrouter.ai/api/v1.
This means we use LangChain's ChatOpenAI class but point it at OpenRouter's
URL instead of OpenAI's. It's like a universal adapter — one interface,
many model providers (Google, Meta, Anthropic, etc.) behind it.

The model ID format is: "provider/model-name:variant"
Example: "google/gemma-3-27b-it:free"  → Google's Gemma 3 27B, free tier
"""

import logging
from langchain_openai import ChatOpenAI
from backend.config.settings import get_settings

logger = logging.getLogger(__name__)


def get_llm(
    temperature: float = 0.3,
    streaming: bool = False,
) -> ChatOpenAI:
    """
    Create and return a configured LLM instance via OpenRouter.
    
    WHY temperature=0.3 (not 0.0 or 0.7)?
    - 0.0 = Fully deterministic. Good for code generation, bad for research
            because it produces repetitive, uncreative summaries.
    - 0.7+ = Creative but unpredictable. Research needs facts, not fiction.
    - 0.3 = Sweet spot for research: factual but with enough variety to
            produce natural-sounding analysis and comparisons.
    
    WHY streaming parameter?
    - For the SSE endpoint (Phase 7), we need token-by-token streaming
      so the frontend shows progress in real-time.
    - For internal node processing, we don't need streaming overhead.
    
    Args:
        temperature: Controls randomness. 0.0 = deterministic, 1.0 = creative.
        streaming: If True, enables token-by-token streaming for SSE.
    
    Returns:
        ChatOpenAI: A configured LLM instance pointed at OpenRouter.
    
    Raises:
        ValidationError: If OPENROUTER_API_KEY is missing from environment.
    """
    settings = get_settings()
    
    logger.info(
        f"Initializing LLM: model={settings.openrouter_model}, "
        f"temperature={temperature}, streaming={streaming}"
    )
    
    # Create the LLM using LangChain's ChatOpenAI class.
    # Since OpenRouter is OpenAI-compatible, we just swap the base URL.
    llm = ChatOpenAI(
        # The model ID on OpenRouter (e.g., "google/gemma-3-27b-it:free")
        model=settings.openrouter_model,
        
        # Our OpenRouter API key (NOT an OpenAI key)
        api_key=settings.openrouter_api_key,
        
        # Point to OpenRouter instead of OpenAI
        base_url=settings.openrouter_base_url,
        
        # Controls output randomness
        temperature=temperature,
        
        # Enable streaming for real-time SSE in the frontend
        streaming=streaming,
        
        # Default headers recommended by OpenRouter for analytics
        # These help OpenRouter track usage and prioritize free-tier users
        default_headers={
            "HTTP-Referer": "http://localhost:8000",  # Your app URL
            "X-Title": "AI Research Agent",            # Your app name
        },
    )
    
    return llm


def get_llm_with_structured_output(output_schema: type, temperature: float = 0.1):
    """
    Create an LLM that returns structured (Pydantic model) output.
    
    WHY STRUCTURED OUTPUT?
    The Planner node needs to return a ResearchPlan object, not free text.
    By binding a Pydantic schema, the LLM is forced to return valid JSON
    that matches our exact data structure. No parsing, no regex, no
    "I hope the LLM formatted it correctly" prayers.
    
    WHY temperature=0.1 for structured output?
    Structured output needs the LLM to follow a strict JSON schema.
    Higher temperatures increase the chance of malformed JSON.
    We use 0.1 (not 0.0) to allow slight variation while keeping
    the output reliable.
    
    Args:
        output_schema: A Pydantic model class that defines the expected output.
        temperature: Lower is more reliable for structured output.
    
    Returns:
        A ChatOpenAI instance bound to produce structured output.
    """
    llm = get_llm(temperature=temperature)
    
    # .with_structured_output() tells the LLM to respond in JSON
    # matching the Pydantic schema. LangChain handles the parsing.
    return llm.with_structured_output(output_schema)
