# ============================================
# AI Research Agent - Routing Logic
# ============================================
"""
Conditional edge functions for the LangGraph research workflow.

WHAT ARE CONDITIONAL EDGES?
---------------------------
In LangGraph, edges define the flow between nodes. There are two types:

1. Static Edges: A → B (always goes to B after A)
   workflow.add_edge("planner", "searcher")

2. Conditional Edges: A → ? (decides at runtime where to go)
   workflow.add_conditional_edges("analyzer", should_continue_research)

Conditional edges are what make the graph DYNAMIC. Instead of a fixed
pipeline, the graph can make decisions based on the current state.

WHY SEPARATE FROM THE GRAPH?
----------------------------
Routing logic is its own concern. By separating it:
- We can test routing decisions independently
- The graph construction file stays clean
- We can add new routes without modifying existing ones
"""

import logging
from backend.state.research_state import ResearchState

logger = logging.getLogger(__name__)


def should_search(state: ResearchState) -> str:
    """
    Decide whether to proceed to searching or skip to reporting.
    
    Called after the Planner node.
    
    Returns:
        "searcher" if there are search queries to execute
        "reporter" if there are no queries (shouldn't normally happen)
    """
    search_queries = state.get("search_queries", [])
    
    if search_queries:
        logger.info(f"🔀 Routing: Proceeding to search ({len(search_queries)} queries)")
        return "searcher"
    else:
        logger.warning("🔀 Routing: No search queries, skipping to reporter")
        return "reporter"


def should_extract(state: ResearchState) -> str:
    """
    Decide whether to extract content or skip to reporting.
    
    Called after the Searcher node.
    
    Returns:
        "extractor" if there are search results to extract from
        "reporter" if search returned no results
    """
    search_results = state.get("search_results", [])
    
    if search_results:
        logger.info(f"🔀 Routing: Proceeding to extraction ({len(search_results)} results)")
        return "extractor"
    else:
        logger.warning("🔀 Routing: No search results, skipping to reporter")
        return "reporter"


def should_continue_research(state: ResearchState) -> str:
    """
    The MOST IMPORTANT routing decision: continue researching or generate report?
    
    Called after the Analyzer node. This is where ITERATIVE REASONING happens.
    
    The Analyzer can set needs_more_research=True with additional_queries
    if it determines the current information is insufficient. This routes
    the graph BACK to the Searcher for another iteration.
    
    SAFETY: The iteration count is checked in the Analyzer node to prevent
    infinite loops (max_research_iterations setting).
    
    Returns:
        "searcher" if more research is needed (loop back)
        "reporter" if research is sufficient (move forward)
    """
    analysis = state.get("analysis")
    
    if analysis and analysis.needs_more_research and analysis.additional_queries:
        logger.info(
            f"🔀 Routing: More research needed! Looping back to searcher "
            f"with {len(analysis.additional_queries)} new queries"
        )
        return "searcher"
    else:
        logger.info("🔀 Routing: Research sufficient, proceeding to reporter")
        return "reporter"
