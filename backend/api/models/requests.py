# ============================================
# AI Research Agent - API Request/Response Models
# ============================================
"""
Pydantic models for the FastAPI request and response schemas.

WHY SEPARATE MODELS FROM STATE?
-------------------------------
The API models define what the CLIENT sends/receives.
The state models define what the GRAPH processes internally.

These are different concerns:
- Client sends: { "query": "quantum computing" }
- Graph processes: ResearchState with 12+ fields
- Client receives: { "type": "progress", "node": "planner", "message": "..." }

Mixing these would create tight coupling between frontend and backend.
"""

from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    """Request body for the /api/research endpoint."""
    query: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="The research query to investigate",
        examples=["Research the latest advancements in Quantum Computing"],
    )


class ResearchResponse(BaseModel):
    """Final response when research is complete (non-streaming)."""
    report: str = Field(description="The complete research report in Markdown")
    citations_count: int = Field(description="Number of citations in the report")
    sources_analyzed: int = Field(description="Number of sources analyzed")
    status: str = Field(description="Final status of the research")


class ProgressEvent(BaseModel):
    """SSE event sent during research execution."""
    type: str = Field(description="Event type: 'status', 'progress', 'report', 'error', 'done'")
    node: str = Field(default="", description="Current node being executed")
    message: str = Field(default="", description="Human-readable progress message")
    data: dict = Field(default_factory=dict, description="Additional data payload")
