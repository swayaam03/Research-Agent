# ============================================
# AI Research Agent - Tools Unit Tests
# ============================================

from backend.state.research_state import SearchResult, ExtractedContent
from backend.tools.citation_formatter import create_citations, format_citations_section


def test_create_citations():
    """Test citation generation and de-duplication."""
    search_results = [
        SearchResult(url="https://site.com/a", title="Title A", snippet="Snippet A"),
        SearchResult(url="https://site.com/b", title="Title B", snippet="Snippet B"),
    ]
    extracted_content = [
        ExtractedContent(url="https://site.com/a", title="Better Title A", content="Content A", word_count=100),
    ]

    citations = create_citations(search_results, extracted_content)

    assert len(citations) == 2
    # Check that extracted title overrides search title
    cit_a = next(c for c in citations if c.url == "https://site.com/a")
    assert cit_a.title == "Better Title A"


def test_format_citations_section():
    """Test formatting citations into markdown."""
    from backend.state.research_state import Citation

    citations = [
        Citation(id=1, url="https://site.com/a", title="Title A", accessed_date="2026-07-26")
    ]
    formatted = format_citations_section(citations)

    assert "## References" in formatted
    assert "[1] Title A - https://site.com/a" in formatted
