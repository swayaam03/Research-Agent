# ============================================
# AI Research Agent - Research Graph
# ============================================
"""
The main LangGraph StateGraph that orchestrates the entire research pipeline.

THIS FILE IS THE HEART OF THE PROJECT.
=======================================

Here's where everything comes together:
- State schema defines WHAT data flows
- Nodes define WHAT work happens
- Edges define WHEN work happens
- Conditional edges define IF work happens
- The compiled graph IS the autonomous agent

HOW STATEGRAPH WORKS:
---------------------
1. You create a StateGraph with a state schema (our ResearchState)
2. You add nodes (Python functions that transform state)
3. You add edges (connections between nodes)
4. You compile the graph into an executable application
5. You invoke the compiled graph with initial state

The compiled graph:
- Manages state automatically (merges, reducers)
- Handles routing decisions (conditional edges)
- Supports checkpointing (save/resume)
- Enables streaming (SSE events)

VISUALIZATION:
    START → Planner → [should_search?]
                           ↓ yes
                       Searcher → [should_extract?]
                           ↓ yes            ↓ no
                       Extractor         Reporter → END
                           ↓
                       Analyzer → [should_continue?]
                           ↓ yes (loop)     ↓ no
                       Searcher          Reporter → END
"""

import logging
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from backend.state.research_state import ResearchState
from backend.nodes.planner import planner_node
from backend.nodes.searcher import searcher_node
from backend.nodes.extractor import extractor_node
from backend.nodes.analyzer import analyzer_node
from backend.nodes.reporter import reporter_node
from backend.graph.routing import (
    should_search,
    should_extract,
    should_continue_research,
)

logger = logging.getLogger(__name__)


def create_research_graph():
    """
    Construct and compile the research StateGraph.
    
    This function builds the entire research pipeline:
    1. Creates a StateGraph with ResearchState schema
    2. Adds all 5 nodes (planner, searcher, extractor, analyzer, reporter)
    3. Wires them together with edges and conditional edges
    4. Compiles with a MemorySaver checkpointer
    
    Returns:
        A compiled LangGraph application ready for invocation.
    
    ARCHITECTURE NOTES:
    - MemorySaver stores checkpoints in memory (good for development)
    - For production, swap to PostgresSaver for persistence
    - The graph is compiled ONCE and reused for all requests
    """
    logger.info("🏗️ Building research graph...")
    
    # ---- Step 1: Create the StateGraph ----
    # The state schema tells LangGraph what data to track
    # and how to merge updates (reducers)
    workflow = StateGraph(ResearchState)
    
    # ---- Step 2: Add Nodes ----
    # Each node is a Python function: (state) -> state_update
    # Node names are strings used for routing
    workflow.add_node("planner", planner_node)
    workflow.add_node("searcher", searcher_node)
    workflow.add_node("extractor", extractor_node)
    workflow.add_node("analyzer", analyzer_node)
    workflow.add_node("reporter", reporter_node)
    
    # ---- Step 3: Set Entry Point ----
    # The graph always starts at the planner
    workflow.set_entry_point("planner")
    
    # ---- Step 4: Add Edges ----
    # 
    # CONDITIONAL EDGE 1: After planning, decide if we should search
    # Normally yes, but handles edge case of no queries
    workflow.add_conditional_edges(
        "planner",
        should_search,
        {
            "searcher": "searcher",    # Normal path: go search
            "reporter": "reporter",    # Edge case: skip to report
        }
    )
    
    # CONDITIONAL EDGE 2: After searching, decide if we should extract
    # If search returned no results, skip extraction
    workflow.add_conditional_edges(
        "searcher",
        should_extract,
        {
            "extractor": "extractor",  # Normal path: extract content
            "reporter": "reporter",    # Edge case: no results
        }
    )
    
    # STATIC EDGE: Extraction always leads to analysis
    workflow.add_edge("extractor", "analyzer")
    
    # CONDITIONAL EDGE 3: THE ITERATIVE REASONING LOOP
    # After analysis, the agent decides:
    # - "I need more information" → loop back to Searcher
    # - "I have enough" → proceed to Reporter
    workflow.add_conditional_edges(
        "analyzer",
        should_continue_research,
        {
            "searcher": "searcher",    # Loop back for more research
            "reporter": "reporter",    # Sufficient → generate report
        }
    )
    
    # STATIC EDGE: Reporter always ends the graph
    workflow.add_edge("reporter", END)
    
    # ---- Step 5: Compile with Checkpointer ----
    # MemorySaver enables:
    # - State persistence across graph execution
    # - Thread-based isolation (multiple concurrent research sessions)
    # - Human-in-the-loop interruption and resumption
    checkpointer = MemorySaver()
    
    compiled_graph = workflow.compile(checkpointer=checkpointer)
    
    logger.info("✅ Research graph compiled successfully")
    return compiled_graph


# Create a singleton instance of the compiled graph
# This is compiled ONCE at import time and reused for all requests
research_graph = create_research_graph()
