# ============================================
# AI Research Agent - Citation Formatter
# ============================================
"""
Citation management utility for the research report.

WHY DEDICATED CITATION MANAGEMENT?
-----------------------------------
Research without citations is just opinions. This utility ensures:

1. Every source used in the report is properly cited with a number [1], [2], etc.
2. URLs are tracked so the user can verify claims.
3. The citation format is consistent across the entire report.
4. Duplicate URLs are automatically de-duplicated.

This is a utility, not a LangChain tool — it doesn't call external APIs.
It's a pure function that transforms data.
"""

import logging
from datetime import datetime
from backend.state.research_state import Citation, SearchResult, ExtractedContent

logger = logging.getLogger(__name__)


def create_citations(
    search_results: list[SearchResult],
    extracted_content: list[ExtractedContent],
) -> list[Citation]:
    """
    Create numbered citations from search results and extracted content.
    
    Combines information from both sources to build a comprehensive
    citation list. De-duplicates by URL to avoid listing the same
    source twice.
    
    Args:
        search_results: Raw search results with URLs and titles.
        extracted_content: Extracted content with potentially updated titles.
    
    Returns:
        List of Citation objects, numbered starting from 1.
    
    Example:
        >>> citations = create_citations(search_results, extracted_content)
        >>> for c in citations:
        ...     print(f"[{c.id}] {c.title} - {c.url}")
    """
    # Build a URL → title mapping from both sources
    # Extracted content titles are often more accurate (from actual page)
    url_to_title: dict[str, str] = {}
    
    # First pass: titles from search results
    for result in search_results:
        if result.url and result.url not in url_to_title:
            url_to_title[result.url] = result.title
    
    # Second pass: titles from extracted content (override with better titles)
    for content in extracted_content:
        if content.url and content.extraction_success:
            url_to_title[content.url] = content.title
    
    # Create numbered citations
    today = datetime.now().strftime("%Y-%m-%d")
    citations = []
    
    for idx, (url, title) in enumerate(url_to_title.items(), start=1):
        citation = Citation(
            id=idx,
            url=url,
            title=title if title else "Untitled Source",
            accessed_date=today,
        )
        citations.append(citation)
    
    logger.info(f"Created {len(citations)} citations from {len(url_to_title)} unique URLs")
    return citations


def format_citations_section(citations: list[Citation]) -> str:
    """
    Format citations into a Markdown references section.
    
    Produces output like:
    
    ## References
    
    [1] Title of Source 1 - https://example.com/article1 (Accessed: 2025-07-26)
    [2] Title of Source 2 - https://example.com/article2 (Accessed: 2025-07-26)
    
    Args:
        citations: List of Citation objects to format.
    
    Returns:
        Formatted Markdown string for the references section.
    """
    if not citations:
        return "\n## References\n\nNo sources were cited in this report.\n"
    
    lines = ["\n## References\n"]
    for citation in citations:
        accessed = f" (Accessed: {citation.accessed_date})" if citation.accessed_date else ""
        lines.append(f"[{citation.id}] {citation.title} - {citation.url}{accessed}")
    
    return "\n".join(lines) + "\n"
