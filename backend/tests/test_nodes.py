# ============================================
# AI Research Agent - Nodes Unit Tests
# ============================================

from backend.state.research_state import ResearchState, SearchResult, ExtractedContent
from backend.nodes.searcher import searcher_node
from backend.nodes.extractor import extractor_node
from backend.graph.routing import should_search, should_extract, should_continue_research


def test_routing_functions():
    """Test conditional edge functions."""
    state_empty: ResearchState = {"user_query": "test"}
    assert should_search(state_empty) == "reporter"

    state_queries: ResearchState = {"user_query": "test", "search_queries": ["q1"]}
    assert should_search(state_queries) == "searcher"

    state_results: ResearchState = {
        "user_query": "test",
        "search_results": [SearchResult(url="https://site.com", title="Title", snippet="")]
    }
    assert should_extract(state_results) == "extractor"
    assert should_extract(state_empty) == "reporter"
