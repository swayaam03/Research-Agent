# ============================================
# AI Research Agent - State Unit Tests
# ============================================

from backend.state.research_state import (
    ResearchPlan,
    SubQuestion,
    SearchResult,
    ExtractedContent,
    SourceSummary,
    AnalysisResult,
    Citation,
)


def test_research_plan_model():
    """Test creating a valid ResearchPlan model."""
    sub_q = SubQuestion(
        question="What is LangGraph?",
        priority=1,
        search_query="LangGraph python framework features"
    )
    plan = ResearchPlan(
        objective="Compare agent frameworks",
        approach="Comparative analysis",
        sub_questions=[sub_q],
        expected_sections=["Introduction", "Comparison", "Conclusion"]
    )
    assert plan.objective == "Compare agent frameworks"
    assert len(plan.sub_questions) == 1
    assert plan.sub_questions[0].search_query == "LangGraph python framework features"


def test_search_result_model():
    """Test SearchResult model initialization and defaults."""
    res = SearchResult(
        url="https://example.com",
        title="Example Title",
        snippet="A brief snippet",
        relevance_score=0.9,
        query="test query"
    )
    assert res.url == "https://example.com"
    assert res.relevance_score == 0.9


def test_citation_model():
    """Test Citation model creation."""
    cit = Citation(
        id=1,
        url="https://example.com/doc",
        title="Doc Title",
        accessed_date="2026-07-26"
    )
    assert cit.id == 1
    assert cit.url == "https://example.com/doc"
