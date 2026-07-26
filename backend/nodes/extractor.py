# ============================================
# AI Research Agent - Extractor Node
# ============================================
"""
The Extractor node reads web pages and extracts their main content.

WHAT IT DOES:
Takes the URLs from search_results, visits each page, and extracts
the main article text in parallel using Trafilatura (with BS4 fallback).

PERFORMANCE OPTIMIZATION:
Extracts pages concurrently using thread pool workers, cutting extraction
time from ~20 seconds to ~2 seconds.
"""

import logging
from backend.state.research_state import ResearchState
from backend.tools.webpage_reader import read_webpages_parallel
from backend.config.settings import get_settings

logger = logging.getLogger(__name__)


def extractor_node(state: ResearchState) -> dict:
    """
    Content Extraction Node.
    
    Input from state: search_results
    Output to state: extracted_content, status, execution_log
    
    Reads the top N web pages in parallel and extracts their main content.
    Uses the `operator.add` reducer — content accumulates across iterations.
    """
    search_results = state.get("search_results", [])
    settings = get_settings()
    
    if not search_results:
        logger.warning("📄 Extractor: No search results to extract content from")
        return {
            "status": "extracted",
            "execution_log": ["Extractor: No search results available for extraction"],
        }
    
    # Sort by relevance score (highest first) and cap to max_pages_to_read
    sorted_results = sorted(
        search_results, 
        key=lambda r: r.relevance_score, 
        reverse=True
    )
    urls_to_read = sorted_results[:settings.max_pages_to_read]
    
    logger.info(
        f"📄 Extractor: Extracting content concurrently from top {len(urls_to_read)} "
        f"of {len(search_results)} results"
    )
    
    url_list = [r.url for r in urls_to_read]
    extracted = read_webpages_parallel(url_list, max_workers=len(url_list) or 1)
    
    successful = sum(1 for c in extracted if c.extraction_success)
    total_words = sum(c.word_count for c in extracted)
    
    logger.info(f"📄 Extractor: Extracted {successful}/{len(url_list)} pages ({total_words} total words)")
    
    return {
        "extracted_content": extracted,  # APPENDS via reducer
        "status": "extracted",
        "execution_log": [
            f"Extracted content from {successful}/{len(url_list)} pages "
            f"({total_words} total words)"
        ],
    }
