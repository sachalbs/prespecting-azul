"""The per-prospect pipeline as a LangGraph StateGraph: verify -> research -> write.

We own the loop. The human-approval gate lives between draft and send; in Jalon 0
it is enforced via message status across CLI commands. When we graduate to
in-process HITL, it becomes a LangGraph `interrupt()` right after `write` here.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from langgraph.graph import END, START, StateGraph

from azul.enums import EmailStatus
from azul.orchestrator.state import ProspectState
from azul.research import ResearchEngine, get_research_engine
from azul.sourcing import EmailVerifier, get_verifier
from azul.writing import DraftRequest, Writer, get_writer


def build_pipeline(
    *,
    verifier: EmailVerifier | None = None,
    research_engine: ResearchEngine | None = None,
    writer: Writer | None = None,
) -> Any:
    """Compile the pipeline once per run; nodes close over the chosen engines."""
    verifier = verifier or get_verifier()
    research_engine = research_engine or get_research_engine()
    writer = writer or get_writer()

    def verify_node(state: ProspectState) -> dict[str, Any]:
        brief = state["prospect"]
        result = verifier.verify(
            brief.email, full_name=brief.full_name, company_domain=brief.company_domain
        )
        # Fold the dossier into the brief so research + writer can use it.
        signals = dict(brief.signals)
        if result.dossier:
            signals["dossier"] = result.dossier
        enriched = replace(brief, email=result.email or brief.email, signals=signals)
        return {
            "prospect": enriched,
            "email_status": result.status,
            "verify_status": result.verdict,
            "verify_confidence": result.score,
            "resolved_email": result.email,
            "dossier": result.dossier,
        }

    def route_after_verify(state: ProspectState) -> str:
        # Deliverability gate: only a hard INVALID (or an unusable address) stops.
        # Catch-all/unknown proceed — they are flagged, the human decides at review.
        status = state.get("email_status", EmailStatus.UNKNOWN)
        email = state.get("resolved_email") or state["prospect"].email
        if status == EmailStatus.INVALID or not email or "*" in email:
            return "stop"
        return "research"

    def research_node(state: ProspectState) -> dict[str, Any]:
        return {"research": research_engine.research(state["prospect"])}

    def write_node(state: ProspectState) -> dict[str, Any]:
        research = state.get("research")
        hook = research.top_hook if research else None
        draft = writer.write(
            DraftRequest(
                prospect=state["prospect"],
                hook=hook,
                channel="email",
                sender_name=state.get("sender_name"),
                value_prop=state.get("value_prop"),
                procedural_hint=state.get("procedural_hint"),
                relationship_note=state.get("relationship_note"),
            )
        )
        return {"draft": draft}

    graph = StateGraph(ProspectState)
    graph.add_node("verify", verify_node)
    graph.add_node("research", research_node)
    graph.add_node("write", write_node)

    graph.add_edge(START, "verify")
    graph.add_conditional_edges("verify", route_after_verify, {"research": "research", "stop": END})
    graph.add_edge("research", "write")
    graph.add_edge("write", END)
    return graph.compile()
