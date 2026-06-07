"""
Agent Graph - LangGraph workflow orchestrating the multi-agent research pipeline.

Flow:
    User Query → Planner → Researcher → Data Analyst → Strategic Intelligence → Critic ─→ Publisher
                                ↑                                                 │
                                └── (quality < 0.8) ──────────────────────────────┘

Migration: Uses typed ResearchState instead of generic dict for LangSmith
visibility and type safety. All nodes now return partial state updates.
"""
from langgraph.graph import StateGraph, END
from graph.state import ResearchState, create_initial_state
from agents.planner import planner_node
from agents.researcher import researcher_node
from agents.data_analyst import data_analyst_node
from agents.strategic_intelligence import strategic_intelligence_node
from agents.critic import critic_node
from agents.publisher import publisher_node
import json


def should_continue_research(state: dict) -> str:
    """
    Conditional edge: decides whether to loop back to Researcher or proceed to Publisher.
    
    Rules:
    1. Quality >= 0.8 → publish (commercial-grade quality gate)
    2. Hit max iterations → publish with warning
    3. Quality improving → one more loop
    4. Quality not improving (plateau) → publish with warning
    """
    quality = state.get("quality_score", 0)
    iteration = state.get("current_iteration", 0)
    max_iterations = state.get("max_iterations", 3)
    prev_quality = state.get("previous_quality", 0)
    
    # Condition 1: Quality is good enough for commercial use
    if quality >= 0.8:
        print(f"\n   ✅ Quality {quality:.0%} ≥ 80% — proceeding to publish")
        return "publisher"
    
    # Condition 2: Hit max iterations
    if iteration >= max_iterations:
        # warnings uses Annotated[List, operator.add] — return only new items
        print(f"\n   ⚠️ Max iterations ({max_iterations}) reached — publishing anyway")
        return "publisher"
    
    # Condition 3: Quality improving → try again
    if quality > prev_quality + 0.05:  # Meaningful improvement
        print(f"\n   🔄 Quality {quality:.0%} improving (was {prev_quality:.0%}) — researching more")
        return "researcher"
    
    # Condition 4: Plateau → stop
    print(f"\n   ⚠️ Quality plateaued at {quality:.0%} — publishing")
    return "publisher"


def build_research_graph() -> StateGraph:
    """
    Build and compile the LangGraph research workflow.
    
    Uses typed ResearchState for:
    - LangSmith trace visibility (field names appear in traces)
    - Annotated reducers for error_log and warnings (auto-append)
    - Type documentation for developers
    
    Returns:
        Compiled StateGraph ready for execution
    """
    # Create the graph with typed state
    workflow = StateGraph(ResearchState)
    
    # Add nodes
    workflow.add_node("planner", planner_node)
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("data_analyst", data_analyst_node)
    workflow.add_node("strategic_intelligence", strategic_intelligence_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("publisher", publisher_node)
    
    # Define edges
    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "researcher")
    workflow.add_edge("researcher", "data_analyst")
    workflow.add_edge("data_analyst", "strategic_intelligence")
    workflow.add_edge("strategic_intelligence", "critic")
    
    # Conditional edge from critic → researcher (loop) or publisher (done)
    workflow.add_conditional_edges(
        "critic",
        should_continue_research,
        {
            "researcher": "researcher",
            "publisher": "publisher",
        }
    )
    
    workflow.add_edge("publisher", END)
    
    # Compile
    return workflow.compile()


# ── Pre-compiled graph singleton ──────────────────────────────────
_compiled_graph = None

def get_research_graph():
    """Get or create the compiled research graph (singleton)."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_research_graph()
    return _compiled_graph


def run_deep_research(query: str, max_iterations: int = 3) -> dict:
    """
    Run the full multi-agent research pipeline and save results to the DB.
    
    Args:
        query: The user's research question
        max_iterations: Max research loops (default: 3)
    
    Returns:
        Final state dict with all research results
    """
    print(f"\n{'='*60}")
    print(f"🚀 Starting Deep Research: {query}")
    print(f"{'='*60}")
    
    # Create initial state
    initial_state = create_initial_state(query, max_iterations=max_iterations)
    
    # Get compiled graph
    graph = get_research_graph()
    
    # Run the graph
    final_state = graph.invoke(initial_state)
    
    print(f"\n{'='*60}")
    print(f"✅ Research Complete!")
    print(f"   Quality: {final_state.get('quality_score', 0):.0%}")
    print(f"   Sources: {len(final_state.get('sources', []))}")
    print(f"   Metrics: {len(final_state.get('metrics', []))}")
    print(f"   Iterations: {final_state.get('current_iteration', 0)}")
    print(f"{'='*60}\n")
    
    # Save the session to PostgreSQL
    try:
        from database.db import save_research_session
        save_research_session(final_state)
    except Exception as e:
        print(f"   ⚠️ Could not save to database: {e}")
            
    return final_state


if __name__ == "__main__":
    # Test the graph
    result = run_deep_research(
        "What is the current market size and growth rate of electric vehicles in India?",
        max_iterations=2
    )
    
    print("\n=== FINAL REPORT ===\n")
    print(result.get("final_report", "No report generated"))
