from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

# --- Planner Schemas ---

class SubTaskSchema(BaseModel):
    id: str = Field(..., description="Unique ID for the sub-task")
    description: str = Field(..., description="Description of the research task")
    required_data: List[str] = Field(default_factory=list, description="List of required data points")

class PlannerOutput(BaseModel):
    sub_tasks: List[SubTaskSchema] = Field(..., min_length=3, max_length=7, description="List of sub-tasks to execute")
    research_plan: str = Field(..., min_length=100, description="Overall narrative research plan")

# --- Researcher Schemas ---

class SourceSchema(BaseModel):
    url: str = Field(..., description="URL of the source")
    title: str = Field(..., description="Title of the source")
    snippet: str = Field(..., description="Relevant snippet from the source")
    date_published: Optional[str] = Field(None, description="Date the source was published, if available")

class ResearchResultSchema(BaseModel):
    summary: str = Field(..., description="Summary of the findings for a topic")
    key_points: List[str] = Field(default_factory=list, description="Key data points found")

class ResearcherOutput(BaseModel):
    research_results: Dict[str, ResearchResultSchema] = Field(..., description="Map of topic to research results")
    raw_sources: List[SourceSchema] = Field(..., description="List of sources used")
    error_log: List[str] = Field(default_factory=list, description="Any errors encountered during research")

# --- Analyst Schemas ---

class AnalystOutput(BaseModel):
    extracted_data: Dict[str, Any] = Field(..., description="Categorized raw data")
    trends: List[str] = Field(..., min_length=1, description="Identified trends")
    metrics: List[Dict[str, Any]] = Field(default_factory=list, description="Quantitative metrics found")
    charts_data: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Data formatted for Plotly charts. Each dict MUST have 'type' (bar, line, pie), 'title', and 'data' (list of x/y dicts)."
    )
    swot_analysis: Dict[str, List[str]] = Field(..., description="SWOT analysis with strengths, weaknesses, opportunities, threats as lists of strings")

# --- Critic Schemas ---

class CriticOutput(BaseModel):
    quality_score: float = Field(..., ge=0.0, le=1.0, description="Overall quality score from 0.0 to 1.0")
    quality_breakdown: Dict[str, float] = Field(..., description="Score breakdown by dimension")
    issues: List[str] = Field(default_factory=list, description="List of identified issues")
    suggestions: List[str] = Field(default_factory=list, description="Suggestions for improving research")
    verdict: str = Field(..., description="'PASS' or 'NEEDS_MORE_RESEARCH'")

# --- Publisher Schemas ---

class PublisherOutput(BaseModel):
    final_report: str = Field(..., min_length=500, description="The full markdown formatted report")
    executive_summary: str = Field(..., min_length=100, description="A short executive summary")
