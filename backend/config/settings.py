# ============================================
# AI Research Agent - Application Settings
# ============================================
"""
Centralized configuration management using Pydantic Settings.

WHY PYDANTIC SETTINGS?
---------------------
1. Type Safety: Every config value is validated at startup. If OPENROUTER_API_KEY
   is missing, you get a clear error IMMEDIATELY, not a cryptic failure 5 minutes
   into a research run.

2. Single Source of Truth: All configuration lives here. No scattered os.getenv()
   calls across 15 files wondering if you spelled the env var correctly.

3. Auto-documentation: This class IS the documentation of what env vars are needed.
   New developers read this file and know exactly what to configure.

4. Default Values: Sensible defaults for non-sensitive settings (ports, limits)
   while requiring secrets to be explicitly provided.

COMMON BEGINNER MISTAKES:
- Using os.getenv() everywhere → no validation, no type conversion, easy typos
- Hardcoding API keys → security nightmare, can't deploy to different environments
- Not having a .env.example → teammates don't know what env vars are needed
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Pydantic Settings automatically:
    - Reads from .env file
    - Reads from system environment variables (higher priority)
    - Validates types at startup
    - Raises clear errors for missing required fields
    """
    
    # ---- LLM Provider (OpenRouter) ----
    # OpenRouter gives us access to multiple models through a single API key.
    # Free models have a ":free" suffix in their model ID.
    # The key benefit: we can switch models without changing any code,
    # just update this env var.
    openrouter_api_key: str = Field(
        ...,  # ... means REQUIRED — app won't start without it
        description="OpenRouter API key from https://openrouter.ai/keys"
    )
    openrouter_model: str = Field(
        default="google/gemma-3-27b-it:free",
        description="Model ID on OpenRouter. Use ':free' suffix for free models."
    )
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        description="OpenRouter API base URL (OpenAI-compatible endpoint)"
    )
    
    # ---- Search Provider (Tavily) ----
    # Tavily is purpose-built for AI agents. Unlike raw Google search,
    # it returns structured results with relevance scores and content snippets.
    # Free tier: 1000 searches/month — more than enough for development.
    tavily_api_key: str = Field(
        ...,  # REQUIRED
        description="Tavily API key from https://tavily.com/"
    )
    
    # ---- Application Settings ----
    # These have sensible defaults. Override in .env only if needed.
    app_port: int = Field(
        default=8000,
        description="Port for the FastAPI server"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL"
    )
    
    # ---- Research Agent Limits ----
    # These control how much work the agent does per research request.
    # Important for:
    # 1. Cost control (more searches = more API calls)
    # 2. Response time (more pages = slower research)
    # 3. Quality vs Speed tradeoff
    max_search_results: int = Field(
        default=3,
        ge=1, le=10,
        description="Max search results per query"
    )
    max_pages_to_read: int = Field(
        default=3,
        ge=1, le=5,
        description="Max web pages to extract content from"
    )
    max_research_iterations: int = Field(
        default=1,
        ge=1, le=3,
        description="Max research iterations (default 1 for high efficiency)"
    )
    
    # Pydantic Settings configuration
    model_config = {
        "env_file": ".env",          # Load from .env file in project root
        "env_file_encoding": "utf-8",
        "case_sensitive": False,      # ENV_VAR and env_var both work
        "extra": "ignore",           # Ignore extra env vars we don't need
    }


@lru_cache()
def get_settings() -> Settings:
    """
    Get the application settings (cached singleton).
    
    WHY @lru_cache?
    We only want to parse environment variables ONCE at startup,
    not every time a node or tool needs a config value.
    This creates a singleton pattern without the complexity of
    a singleton class.
    
    USAGE:
        from backend.config.settings import get_settings
        settings = get_settings()
        print(settings.openrouter_model)
    """
    return Settings()
