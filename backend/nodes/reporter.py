# ============================================
# AI Research Agent - Reporter Node
# ============================================
"""
The Reporter is the FINAL node in the research pipeline.

WHAT IT DOES:
Takes all the research — plan, summaries, analysis, citations —
and synthesizes it into a professional Markdown research report.

WHY IT'S THE LAST NODE:
The Reporter consumes everything the previous nodes produced.
It needs:
- research_plan (for structure/sections)
- source_summaries (for detailed findings)
- analysis (for agreements/contradictions)
- citations (for references)

The quality of the report directly depends on the quality of all
previous steps. This is why we invest so much in planning and analysis.

OUTPUT FORMAT:
Markdown is chosen because:
1. It's human-readable as plain text
2. It renders beautifully in the frontend
3. It's easy to export to PDF/HTML later
4. It supports inline citations [1], headers, bullet points
"""

import logging
from langchain_core.messages import SystemMessage, HumanMessage
from backend.state.research_state import ResearchState
from backend.services.llm_service import get_llm
from backend.tools.citation_formatter import create_citations, format_citations_section
from backend.prompts.reporter_prompts import REPORTER_SYSTEM_PROMPT, REPORTER_HUMAN_PROMPT

logger = logging.getLogger(__name__)


def reporter_node(state: ResearchState) -> dict:
    """
    Report Generation Node.
    
    Input from state: research_plan, source_summaries, analysis,
                      search_results, extracted_content
    Output to state: citations, final_report, status, execution_log
    
    Generates the final Markdown report and appends the references section.
    """
    research_plan = state.get("research_plan")
    source_summaries = state.get("source_summaries", [])
    analysis = state.get("analysis")
    search_results = state.get("search_results", [])
    extracted_content = state.get("extracted_content", [])
    
    logger.info("📝 Reporter: Generating final research report")
    
    # ---- Step 1: Create citations ----
    citations = create_citations(search_results, extracted_content)
    
    # ---- Step 2: Prepare data for the report prompt ----
    objective = (
        research_plan.objective if research_plan
        else state.get("user_query", "Research Report")
    )
    approach = research_plan.approach if research_plan else "General research"
    expected_sections = (
        ", ".join(research_plan.expected_sections) if research_plan
        else "Introduction, Findings, Analysis, Conclusion"
    )
    
    # Format summaries for the prompt
    formatted_summaries = "\n\n".join(
        f"### [{i+1}] {s.title}\nURL: {s.url}\n{s.summary}"
        for i, s in enumerate(source_summaries)
    ) if source_summaries else "No source summaries available."
    
    # Format analysis results
    agreements = "\n".join(
        f"- {a}" for a in (analysis.agreements if analysis else [])
    ) or "None identified."
    
    contradictions = "\n".join(
        f"- {c}" for c in (analysis.contradictions if analysis else [])
    ) or "None identified."
    
    unique_findings = "\n".join(
        f"- {u}" for u in (analysis.unique_findings if analysis else [])
    ) or "None identified."
    
    confidence = (
        analysis.confidence_assessment if analysis
        else "Unable to assess confidence."
    )
    
    # Format citations for the prompt
    formatted_citations = "\n".join(
        f"[{c.id}] {c.title} - {c.url}" for c in citations
    ) if citations else "No citations available."
    
    # ---- Step 3: Generate the report ----
    try:
        llm = get_llm(temperature=0.4)  # Slightly higher temp for natural writing
        
        messages = [
            SystemMessage(content=REPORTER_SYSTEM_PROMPT),
            HumanMessage(content=REPORTER_HUMAN_PROMPT.format(
                research_objective=objective,
                approach=approach,
                expected_sections=expected_sections,
                formatted_summaries=formatted_summaries,
                agreements=agreements,
                contradictions=contradictions,
                unique_findings=unique_findings,
                confidence=confidence,
                formatted_citations=formatted_citations,
            )),
        ]
        
        response = llm.invoke(messages)
        report_body = response.content
        
        # ---- Step 4: Append references section ----
        references = format_citations_section(citations)
        final_report = report_body + "\n" + references
        
        logger.info(
            f"📝 Reporter: Generated report "
            f"({len(final_report)} chars, {len(citations)} citations)"
        )
        
        return {
            "citations": citations,
            "final_report": final_report,
            "status": "completed",
            "execution_log": [
                f"Generated research report ({len(final_report)} chars) "
                f"with {len(citations)} citations"
            ],
        }
        
    except Exception as e:
        logger.error(f"📝 Reporter: Failed to generate report: {str(e)}")
        
        # Fallback: create a minimal report from available data
        fallback_report = _create_fallback_report(
            objective, source_summaries, citations
        )
        
        return {
            "citations": citations,
            "final_report": fallback_report,
            "status": "completed",
            "errors": [f"Report generation error: {str(e)}. Using fallback report."],
            "execution_log": ["Reporter: Used fallback report due to LLM error"],
        }


def _create_fallback_report(
    objective: str,
    summaries: list,
    citations: list,
) -> str:
    """
    Create a minimal report when the LLM fails.
    
    Better to return something useful than nothing at all.
    This demonstrates graceful degradation in production systems.
    """
    report = f"# Research Report: {objective}\n\n"
    report += "## Summary of Sources\n\n"
    
    if summaries:
        for i, s in enumerate(summaries, 1):
            report += f"### Source {i}: {s.title}\n"
            report += f"{s.summary}\n\n"
    else:
        report += "No sources were successfully analyzed.\n\n"
    
    report += format_citations_section(citations)
    return report
