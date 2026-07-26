# ============================================
# AI Research Agent - Research API Routes
# ============================================
"""
FastAPI routes for the research endpoint.

SSE (Server-Sent Events) EXPLAINED:
------------------------------------
When the user submits a research query, they don't want to wait 60 seconds
for a response with no feedback. SSE lets us stream real-time progress:

1. User submits query via POST /api/research
2. Server starts the LangGraph execution
3. As each node completes, server sends an SSE event:
   - "Planning research..." 
   - "Searching 5 queries..."
   - "Extracting content from 3 pages..."
   - "Analyzing sources..."
   - "Generating report..."
4. Finally, the complete report is sent
5. Connection closes

WHY SSE INSTEAD OF WEBSOCKETS?
- SSE is unidirectional (server → client), which is all we need
- SSE uses standard HTTP (works through all proxies/load balancers)
- SSE auto-reconnects if the connection drops
- SSE is simpler to implement and debug
- WebSockets are needed only for bidirectional communication
"""

import json
import uuid
import logging
import asyncio
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from backend.api.models.requests import ResearchRequest
from backend.graph.research_graph import research_graph

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["research"])


@router.post("/research")
async def run_research(request: ResearchRequest):
    """
    Execute a research query and stream progress via SSE.
    
    This endpoint:
    1. Creates a unique thread ID for the research session
    2. Invokes the LangGraph research pipeline
    3. Streams progress events as each node completes
    4. Sends the final report when done
    
    Returns:
        StreamingResponse with SSE events (text/event-stream)
    """
    query = request.query
    thread_id = str(uuid.uuid4())
    
    logger.info(f"📨 New research request: '{query}' (thread: {thread_id})")
    
    return StreamingResponse(
        _stream_research(query, thread_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Prevent Nginx buffering
        },
    )


async def _stream_research(query: str, thread_id: str):
    """
    Async generator that runs the research graph and yields SSE events.
    
    HOW THIS WORKS:
    LangGraph's .stream() method yields updates as each node completes.
    We transform these into SSE-formatted events that the frontend
    can parse with EventSource API.
    
    SSE FORMAT:
    Each event is a line starting with "data: " followed by JSON.
    Events are separated by two newlines.
    
    Example:
        data: {"type": "status", "node": "planner", "message": "Creating research plan..."}
        
        data: {"type": "status", "node": "searcher", "message": "Searching 5 queries..."}
        
        data: {"type": "report", "data": {"report": "# Research Report..."}}
        
        data: [DONE]
    """
    # Map node names to user-friendly descriptions
    node_descriptions = {
        "planner": "📋 Creating research plan...",
        "searcher": "🔍 Searching the web...",
        "extractor": "📄 Reading web pages...",
        "analyzer": "🧠 Analyzing sources...",
        "reporter": "📝 Generating report...",
    }
    
    try:
        # Send initial event
        yield _format_sse({
            "type": "status",
            "node": "start",
            "message": "🚀 Starting research...",
        })
        
        # Configure the graph invocation
        # thread_id enables checkpointing — each research session
        # has its own state that can be resumed if interrupted
        config = {"configurable": {"thread_id": thread_id}}
        initial_state = {"user_query": query, "current_iteration": 0}
        
        # Stream graph execution
        # stream() yields (node_name, state_update) as each node completes
        for event in research_graph.stream(initial_state, config=config):
            # event is a dict: {node_name: state_update}
            for node_name, node_output in event.items():
                # Skip internal LangGraph nodes
                if node_name.startswith("__"):
                    continue
                
                # Get user-friendly description
                description = node_descriptions.get(
                    node_name, f"Processing {node_name}..."
                )
                
                # Extract execution log entries for detailed progress
                log_entries = node_output.get("execution_log", [])
                detail = log_entries[-1] if log_entries else ""
                
                # Send progress event
                yield _format_sse({
                    "type": "status",
                    "node": node_name,
                    "message": description,
                    "data": {"detail": detail},
                })
                
                # If reporter node completed, send the report
                if node_name == "reporter" and "final_report" in node_output:
                    yield _format_sse({
                        "type": "report",
                        "node": "reporter",
                        "message": "Research complete!",
                        "data": {
                            "report": node_output["final_report"],
                            "citations_count": len(node_output.get("citations", [])),
                        },
                    })
                
                # Small delay to prevent overwhelming the client
                await asyncio.sleep(0.1)
        
        # Send completion event
        yield _format_sse({
            "type": "done",
            "node": "end",
            "message": "✅ Research completed successfully!",
        })
        
    except Exception as e:
        logger.error(f"Research pipeline error: {str(e)}")
        yield _format_sse({
            "type": "error",
            "node": "system",
            "message": f"Research failed: {str(e)}",
        })
    
    # Final SSE termination signal
    yield "data: [DONE]\n\n"


def _format_sse(data: dict) -> str:
    """Format a dictionary as an SSE data event."""
    return f"data: {json.dumps(data)}\n\n"
