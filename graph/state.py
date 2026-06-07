"""
Research State Schema - Shared state for the multi-agent LangGraph workflow.
This is the central data structure that all agents read from and write to.

Migration: Added Annotated reducers for append-only list fields (error_log, warnings)
so LangGraph properly merges data from different nodes.
"""
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from dataclasses import dataclass, field
import operator


@dataclass
class SubTask:
    """A single research sub-task created by the Planner."""
    id: int
    query: str
    priority: int = 1          # 1=highest, 5=lowest
    status: str = "pending"    # pending | in_progress | complete | failed
    result: str = ""           # Research result summary
    sources: list = field(default_factory=list)  # [{title, url, snippet}]
    data_points: dict = field(default_factory=dict)  # Extracted metrics


def _overwrite_list(existing: List, new: List) -> List:
    """Reducer that overwrites the list (default behavior for non-append fields)."""
    return new


class ResearchState(TypedDict, total=False):
    """
    The shared state that flows through the LangGraph workflow.
    Every agent reads from and writes to this state.
    
    Flow: User Query → Planner → Researcher → Data Analyst → Strategic Intelligence → Critic → Publisher
                                    ↑                                                          |
                                    └── (if quality < 0.8) ────────────────────────────────────┘
    
    Fields with Annotated[..., operator.add] are append-only:
    each node returns ONLY new items, and LangGraph concatenates them.
    
    All other fields use last-write-wins semantics.
    """
    # ── Input ──────────────────────────────────────────────
    session_id: str                        # UUID of the research session
    original_query: str                    # The user's original research question
    
    # ── Planner Output ─────────────────────────────────────
    sub_tasks: List[Dict[str, Any]]        # List of sub-tasks (serialized SubTask dicts)
    research_plan: str                     # Human-readable plan description
    
    # ── Researcher Output ──────────────────────────────────
    raw_content: List[Dict[str, Any]]      # [{title, url, content, source_query}]
    sources: List[Dict[str, str]]          # [{title, url, snippet}]
    research_summary: str                  # Combined research summary
    
    # ── Data Analyst Output ────────────────────────────────
    metrics: List[Dict[str, Any]]          # [{name, value, source, confidence}]
    trends: List[str]                      # Identified trends
    charts_data: List[Dict[str, Any]]      # Plotly chart definitions
    comparisons: List[Dict[str, Any]]      # Comparison tables
    analysis_summary: str                  # Data Analyst's synthesis (non-strategic)
    
    # ── Strategic Intelligence Output ──────────────────────
    strategic_reasoning: Dict[str, Any]    # Causal chains and logic
    strategic_drivers: List[Dict[str, Any]] # Expanded macro/market/industry drivers
    valuation_analysis: Dict[str, Any]     # Valuation metrics and matrix
    scenario_forecasts: Dict[str, Any]     # Bear/Base/Bull scenario forecasts
    contrarian_intelligence: Dict[str, Any]# Bull/Bear/Neutral cases, Stress Test
    strategic_score: Dict[str, Any]        # Overall investment score
    confidence_calibration: Dict[str, Any] # Confidence score and reasons
    investment_thesis: Dict[str, Any]      # Why this, why now, upside, downside, catalyst, risk
    executive_recommendations: Dict[str, Any] # Top recommendations, priorities, actions
    
    # ── Critic Output ──────────────────────────────────────
    quality_score: float                   # 0.0 - 1.0 overall quality
    quality_breakdown: Dict[str, float]    # {completeness, accuracy, source_diversity, freshness}
    issues: List[str]                      # Specific problems found
    suggestions: List[str]                 # What to research more
    
    # ── Publisher Output ───────────────────────────────────
    final_report: str                      # The complete markdown report
    executive_summary: str                 # Short executive summary
    swot_analysis: Dict[str, List[str]]    # {strengths, weaknesses, opportunities, threats}
    
    # ── Control Flow ───────────────────────────────────────
    current_iteration: int                 # How many research loops we've done
    max_iterations: int                    # Hard cap on loops (default: 3)
    previous_quality: float                # Quality from last iteration (for plateau detection)
    
    # ── Meta (append-only via Annotated reducers) ──────────
    error_log: Annotated[List[str], operator.add]    # Errors from any agent (non-fatal)
    warnings: Annotated[List[str], operator.add]     # Warnings (e.g., "quality plateaued")
    total_cost: float                      # Running API cost in USD
    status: str                            # Current status message for UI


def create_initial_state(query: str, max_iterations: int = 3, session_id: str = None) -> dict:
    """
    Create the initial state dict for a new research session.
    
    Args:
        query: The user's research question
        max_iterations: Maximum research loops before forced publish
        session_id: Optional ID for the session, generated if None
    
    Returns:
        Initial state dict ready for the graph
    """
    import uuid
    return {
        "session_id": session_id or str(uuid.uuid4()),
        "original_query": query,
        "sub_tasks": [],
        "research_plan": "",
        "raw_content": [],
        "sources": [],
        "research_summary": "",
        "metrics": [],
        "trends": [],
        "comparisons": [],
        "analysis_summary": "",
        "strategic_reasoning": {},
        "strategic_drivers": [],
        "valuation_analysis": {},
        "scenario_forecasts": {},
        "contrarian_intelligence": {},
        "strategic_score": {},
        "confidence_calibration": {},
        "investment_thesis": {},
        "executive_recommendations": {},
        "quality_score": 0.0,
        "quality_breakdown": {},
        "issues": [],
        "suggestions": [],
        "final_report": "",
        "executive_summary": "",
        "swot_analysis": {},
        "current_iteration": 0,
        "max_iterations": max_iterations,
        "previous_quality": 0.0,
        "error_log": [],
        "warnings": [],
        "total_cost": 0.0,
        "status": "Starting research...",
    }
