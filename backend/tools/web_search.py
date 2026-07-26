# ============================================
# AI Research Agent - Web Search Tool
# ============================================
"""
Web search tool using Tavily API.

WHY TAVILY INSTEAD OF RAW GOOGLE SEARCH?
-----------------------------------------
1. Structured Results: Tavily returns JSON with title, URL, content snippet,
   and relevance scores. Google Search API returns HTML you'd need to parse.

2. AI-Optimized: Tavily was built specifically for AI agents. Results are
   pre-filtered for relevance and include content snippets that LLMs can
   immediately work with.

3. Free Tier: 1000 searches/month is generous for development and small projects.

4. Simple Integration: One function call, no OAuth, no custom parsers.

TOOL DESIGN PRINCIPLES:
-----------------------
- Tools should be PURE FUNCTIONS: input → output, no side effects on state.
- Tools should handle their own errors gracefully (return empty list, not crash).
- Tools should be independently testable (no dependency on LangGraph state).
- Tool docstrings are CRITICAL: the LLM reads them to decide when to call the tool.
"""

import logging
from tavily import TavilyClient
from backend.config.settings import get_settings
from backend.state.research_state import SearchResult

logger = logging.getLogger(__name__)


def search_web(query: str, max_results: int = 5) -> list[SearchResult]:
    """
    Search the web using Tavily API and return structured results.
    
    This is the agent's "eyes" into the internet. Given a search query,
    it returns a list of relevant web pages with titles, URLs, and snippets.
    
    Args:
        query: The search query string (e.g., "quantum computing 2025 breakthroughs")
        max_results: Maximum number of results to return (default: 5)
    
    Returns:
        List of SearchResult objects with url, title, snippet, and relevance score.
        Returns empty list if search fails (graceful degradation).
    
    Example:
        >>> results = search_web("LangGraph vs CrewAI comparison")
        >>> for r in results:
        ...     print(f"{r.title}: {r.url}")
    """
    settings = get_settings()
    
    try:
        logger.info(f"Searching web for: '{query}' (max_results={max_results})")
        
        # Initialize Tavily client
        client = TavilyClient(api_key=settings.tavily_api_key)
        
        # Execute search
        # search_depth="advanced" gives better results but uses more API quota
        # include_raw_content=False because we'll extract content ourselves
        response = client.search(
            query=query,
            max_results=max_results,
            search_depth="basic",       # "basic" is faster, "advanced" is more thorough
            include_raw_content=False,   # We extract content separately in the Extractor
            include_answer=False,        # We don't need Tavily's AI-generated answer
        )
        
        # Convert Tavily response to our SearchResult model
        results = []
        for item in response.get("results", []):
            result = SearchResult(
                url=item.get("url", ""),
                title=item.get("title", "Untitled"),
                snippet=item.get("content", ""),
                relevance_score=item.get("score", 0.0),
                query=query,
            )
            results.append(result)
        
        logger.info(f"Found {len(results)} results for: '{query}'")
        return results
        
    except Exception as e:
        # GRACEFUL DEGRADATION: Don't crash the entire research pipeline
        # just because one search failed. Log the error and return empty.
        logger.error(f"Web search failed for '{query}': {str(e)}")
        return []
