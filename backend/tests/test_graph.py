# ============================================
# AI Research Agent - Graph Compilation Tests
# ============================================

from backend.graph.research_graph import research_graph


def test_research_graph_compilation():
    """Verify that the LangGraph StateGraph compiles and has all required nodes."""
    nodes = list(research_graph.get_graph().nodes.keys())
    expected_nodes = ['__start__', 'planner', 'searcher', 'extractor', 'analyzer', 'reporter', '__end__']

    for expected in expected_nodes:
        assert expected in nodes, f"Expected node '{expected}' not found in graph"
