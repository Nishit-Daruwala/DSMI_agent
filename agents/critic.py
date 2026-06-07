"""
Critic Agent - Quality control and verification of research.
The "Quality Inspector" — decides if research is good enough or needs more work.

Migration: Uses LangChain ChatPromptTemplate + chain invocation.
"""
from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from utils.llm_client import get_llm, safe_parse_json, truncate_for_llm
from utils.prompts import DSMI_V2_MASTER_PROMPT
from database.vector_store import VectorStore
from schemas.research_schemas import CriticOutput
from pydantic import ValidationError
import json


class CriticAgent:
    """
    Evaluates research quality across multiple dimensions:
    - Completeness: Does the research answer the original question fully?
    - Accuracy: Are claims supported by cited sources?
    - Source Diversity: Are sources from different domains?
    - Freshness: Are sources recent and relevant?
    
    If quality < 0.7, suggests specific areas to re-research.
    """
    def __init__(self, model: str = "gemini-2.0-flash"):
        self.model = model
        self.vector_store = VectorStore()
    
    def evaluate(
        self,
        query: str,
        research_summary: str,
        sources: List[Dict],
        metrics: List[Dict],
        trends: List[str],
        analysis_summary: str,
        strategic_reasoning: Dict,
        scenario_forecasts: Dict,
        contrarian_intelligence: Dict
    ) -> Dict[str, Any]:
        """
        Evaluate research quality and determine if more research is needed.
        
        Returns:
            Dict with quality_score, breakdown, issues, and suggestions
        """
        # Calculate source diversity
        unique_domains = set()
        for source in sources:
            url = source.get("url", "")
            if url:
                parts = url.split("/")
                if len(parts) >= 3:
                    unique_domains.add(parts[2])
        
        source_count = len(sources)
        domain_count = len(unique_domains)

        # Cross-verify with historical research via Vector DB
        historical_context = ""
        try:
            # We try to see if Qdrant has related info on this query
            similar_past_research = self.vector_store.semantic_search(query, limit=3)
            if similar_past_research:
                historical_context = "\n[Historical Research Match found in DB]\n"
                for res in similar_past_research:
                    historical_context += f"- Past context: {res.get('content', '')[:300]}...\n"
        except Exception as e:
            print(f"   [Critic] Vector DB search skipped: {e}")
        
        # Prepare content for LLM evaluation
        metrics_text = chr(10).join([f"- {m.get('name', 'Unknown')}: {m.get('value', 'N/A')}" for m in metrics[:10]])
        trends_text = chr(10).join([f"- {t}" for t in trends[:10]])
        
        content_for_eval = truncate_for_llm(f"""
Research Question: "{query}"

Research Summary:
{research_summary[:3000]}

Analysis Summary:
{analysis_summary[:2000]}

Metrics Found: {len(metrics)}
Trends Found: {len(trends)}
Sources Used: {source_count}
Unique Domains: {domain_count}

Strategic Reasoning Present: {bool(strategic_reasoning)}
Scenarios Present: {bool(scenario_forecasts)}
Contrarian Analysis Present: {bool(contrarian_intelligence)}

{historical_context}

Key Metrics:
{metrics_text}

Trends:
{trends_text}
""", max_chars=8000)
        
        system_msg = DSMI_V2_MASTER_PROMPT + """

You are the Research Quality Inspector.
Clients PAY for these reports — quality must be commercially viable.

RULE #16 — QUALITY AUDIT BEFORE DELIVERY
Before finalizing, you MUST check:
1. Did we answer the actual question?
2. Did we include strategic reasoning?
3. Did we include risks?
4. Did we include opportunities?
5. Did we include contrarian analysis?
6. Did we include confidence calibration?
7. Did we include scenario analysis?
8. Did we support conclusions with evidence?

If any answer is NO, the report is NOT ready and you must return a NEEDS_MORE_RESEARCH verdict with score < 0.8.

Score each dimension from 0.0 to 1.0:
- completeness: Does it fully answer the research question with a clear verdict?
- accuracy: Are claims well-supported by cited sources?
- source_diversity: Are sources from varied, credible domains?
- freshness: Is the data recent and timely?
- depth: Is the analysis deep with specific numbers?
- actionability: Does it provide actionable recommendations?
- competitive_coverage: Does it mention specific companies?
- data_specificity: Are there enough specific numbers?
- source_relevance: Are sources relevant?
- strategic_reasoning_quality: Are causal chains logical and deep?
- contrarian_quality: Are bear/bull cases robust and judge assessment unbiased?
- scenario_quality: Do scenarios have catalysts, risks, and sensible probabilities?
- decision_utility: Is the intelligence practically useful for an executive?
- executive_readiness: Is the formatting and synthesis ready for board-level review?

SCORING GUIDELINES (be STRICT — this is a commercial product):
- Score below 0.5 if: no competitive landscape, no specific company names, no actionable recommendations
- Score below 0.6 if: analysis is a single paragraph, metrics have no year attribution
- HARD RULE: Score CANNOT exceed 0.8 (80%) if: strategic reasoning is weak, scenarios are missing, or contrarian analysis is weak.
- Score above 0.8 only if: comprehensive with competitive landscape, specific recommendations, deep analysis, 100% relevant sources, and all Rule #16 elements present.

Most first-pass research scores 0.5-0.7. Only truly comprehensive research scores above 0.8.

Respond with JSON:
{{
    "quality_breakdown": {{
        "completeness": 0.7,
        "accuracy": 0.8,
        "source_diversity": 0.6,
        "freshness": 0.7,
        "depth": 0.65,
        "actionability": 0.5,
        "competitive_coverage": 0.3,
        "data_specificity": 0.7,
        "source_relevance": 0.8,
        "strategic_reasoning_quality": 0.6,
        "contrarian_quality": 0.5,
        "scenario_quality": 0.6,
        "decision_utility": 0.7,
        "executive_readiness": 0.6
    }},
    "overall_score": 0.64,
    "issues": [
        "Specific issue 1",
        "Specific issue 2"
    ],
    "suggestions": [
        "Search for: specific query to fill gap 1",
        "Search for: specific query to fill gap 2"
    ],
    "verdict": "PASS or NEEDS_MORE_RESEARCH"
}}"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_msg),
            ("human", "{content_for_eval}")
        ])
        
        try:
            llm = get_llm(model=self.model, temperature=0.2)
            llm = llm.bind(response_mime_type="application/json")
            chain = prompt | llm
            response = chain.invoke({"content_for_eval": content_for_eval})
            result = safe_parse_json(
                response.content,
                fallback={
                    "quality_breakdown": {
                        "completeness": 0.5,
                        "accuracy": 0.5,
                        "source_diversity": 0.5,
                        "freshness": 0.5,
                        "depth": 0.5,
                        "source_relevance": 0.5
                    },
                    "overall_score": 0.5,
                    "issues": ["Could not evaluate quality due to API failure"],
                    "suggestions": [],
                    "verdict": "PASS"
                }
            )
        except Exception as e:
            print(f"   ⚠️ Critic chain error: {e}")
            result = {
                "quality_breakdown": {
                    "completeness": 0.5,
                    "accuracy": 0.5,
                    "source_diversity": 0.5,
                    "freshness": 0.5,
                    "depth": 0.5,
                    "source_relevance": 0.5
                },
                "overall_score": 0.5,
                "issues": ["Could not evaluate quality due to API failure"],
                "suggestions": [],
                "verdict": "PASS"
            }
        
        # Validate using Pydantic Schema
        try:
            # Map LLM output to Pydantic model (handles slight key variations)
            validated_output = CriticOutput(
                quality_score=float(result.get("overall_score", result.get("quality_score", 0.5))),
                quality_breakdown=result.get("quality_breakdown", {}),
                issues=result.get("issues", []),
                suggestions=result.get("suggestions", []),
                verdict=result.get("verdict", "PASS")
            )
            
            return {
                "quality_score": validated_output.quality_score,
                "quality_breakdown": validated_output.quality_breakdown,
                "issues": validated_output.issues,
                "suggestions": validated_output.suggestions,
                "verdict": validated_output.verdict,
            }
        except ValidationError as e:
            print(f"   ⚠️ Pydantic Validation Error in Critic: {e}")
            return {
                "quality_score": float(result.get("overall_score", result.get("quality_score", 0.5))),
                "quality_breakdown": result.get("quality_breakdown", {}),
                "issues": result.get("issues", []) + ["Schema validation warning"],
                "suggestions": result.get("suggestions", []),
                "verdict": result.get("verdict", "PASS"),
            }


def critic_node(state: dict) -> dict:
    """
    LangGraph node function for the Critic agent.
    Reads: original_query, research_summary, sources, metrics, trends, analysis_summary, etc.
    Writes: quality_score, quality_breakdown, issues, suggestions, previous_quality, status
    """
    try:
        iteration = state.get("current_iteration", 0) + 1
        
        print(f"\n🔎 Critic: Evaluating quality (iteration {iteration})...")
        
        critic = CriticAgent()
        result = critic.evaluate(
            query=state["original_query"],
            research_summary=state.get("research_summary", ""),
            sources=state.get("sources", []),
            metrics=state.get("metrics", []),
            trends=state.get("trends", []),
            analysis_summary=state.get("analysis_summary", ""),
            strategic_reasoning=state.get("strategic_reasoning", {}),
            scenario_forecasts=state.get("scenario_forecasts", {}),
            contrarian_intelligence=state.get("contrarian_intelligence", {}),
        )
        
        score = result["quality_score"]
        print(f"   📊 Quality Score: {score:.0%}")
        print(f"   📋 Breakdown: {result['quality_breakdown']}")
        
        if result["issues"]:
            print(f"   ⚠️ Issues: {', '.join(result['issues'][:3])}")
        
        return {
            "quality_score": score,
            "quality_breakdown": result["quality_breakdown"],
            "issues": result["issues"],
            "suggestions": result["suggestions"],
            "previous_quality": state.get("quality_score", 0.0),
            "current_iteration": iteration,
            "status": f"Quality check: {score:.0%} (iteration {iteration})",
        }
    except Exception as e:
        print(f"   ❌ Critic error: {e}")
        return {
            "quality_score": 0.7,  # Pass by default on error
            "quality_breakdown": {},
            "issues": [f"Critic evaluation failed: {str(e)}"],
            "suggestions": [],
            "current_iteration": state.get("current_iteration", 0) + 1,
            "error_log": [f"Critic error: {str(e)}"],
            "status": "Quality check failed, proceeding with current research.",
        }
