# ============================================
# AI Research Agent - Planner Node
# ============================================
"""
The Planner is the FIRST node in the research pipeline.

WHAT IT DOES:
Takes the user's raw query and produces a structured research plan
with sub-questions and optimized search queries.

WHY IT'S NEEDED:
If we just searched the user's query directly, we'd get generic results.
By decomposing "Compare LangGraph and CrewAI" into specific sub-questions like:
- "LangGraph architecture features capabilities"
- "CrewAI architecture features capabilities"
- "LangGraph vs CrewAI performance benchmarks 2025"
we get much more targeted, useful search results.

This is the "think before you act" principle — plan first, then execute.

NODE DESIGN PATTERN:
Every node follows the same pattern:
1. Receive the full state
2. Read what it needs from state
3. Do its work (LLM calls, tool usage)
4. Return ONLY the state fields it updates (delta)
"""

import logging
from langchain_core.messages import SystemMessage, HumanMessage
from backend.state.research_state import ResearchState, ResearchPlan
from backend.services.llm_service import get_llm_with_structured_output
from backend.prompts.planner_prompts import PLANNER_SYSTEM_PROMPT, PLANNER_HUMAN_PROMPT

logger = logging.getLogger(__name__)


def planner_node(state: ResearchState) -> dict:
    """
    Research Planning Node.
    
    Input from state: user_query
    Output to state: research_plan, search_queries, status, execution_log
    
    This node uses STRUCTURED OUTPUT to force the LLM to return
    a valid ResearchPlan object. No parsing, no regex, no hoping
    the LLM formatted it correctly.
    """
    user_query = state["user_query"]
    logger.info(f"📋 Planner: Creating research plan for: '{user_query}'")
    
    try:
        # Get an LLM that returns structured ResearchPlan output
        llm = get_llm_with_structured_output(ResearchPlan, temperature=0.3)
        
        # Create the prompt messages
        messages = [
            SystemMessage(content=PLANNER_SYSTEM_PROMPT),
            HumanMessage(content=PLANNER_HUMAN_PROMPT.format(user_query=user_query)),
        ]
        
        # Invoke the LLM — it returns a ResearchPlan object directly
        research_plan: ResearchPlan = llm.invoke(messages)
        
        # Extract search queries from the plan's sub-questions
        search_queries = [sq.search_query for sq in research_plan.sub_questions]
        
        logger.info(
            f"📋 Planner: Generated plan with {len(research_plan.sub_questions)} "
            f"sub-questions and {len(search_queries)} search queries"
        )
        
        # Return ONLY the state fields this node updates (delta pattern)
        return {
            "research_plan": research_plan,
            "search_queries": search_queries,
            "status": "planned",
            "execution_log": [
                f"Research plan created with {len(search_queries)} search queries: "
                f"{', '.join(search_queries[:3])}{'...' if len(search_queries) > 3 else ''}"
            ],
        }
        
    except Exception as e:
        logger.error(f"📋 Planner: Failed to create research plan: {str(e)}")
        # Even on failure, we return a state update so the graph can continue
        # with fallback search queries derived directly from the user query
        return {
            "research_plan": None,
            "search_queries": [user_query],  # Fallback: search the raw query
            "status": "planned",
            "errors": [f"Planner error: {str(e)}. Using raw query as fallback."],
            "execution_log": [f"Planner failed, falling back to raw query search"],
        }
