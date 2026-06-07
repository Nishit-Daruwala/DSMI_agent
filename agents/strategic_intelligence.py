"""
Strategic Intelligence Agent - Transforms analytical findings into decision-grade intelligence.
"""
from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from utils.llm_client import get_llm, safe_parse_json, truncate_for_llm
from utils.prompts import DSMI_STRATEGIC_INTELLIGENCE_PROMPT

class StrategicIntelligenceAgent:
    def __init__(self, model: str = "gemini-2.0-flash"):
        self.model = model
    
    def analyze(self, query: str, research_summary: str, metrics: List[Dict], trends: List[str], comparisons: List[Dict], analysis_summary: str, sources: List[Dict]) -> Dict[str, Any]:
        metrics_text = "\n".join([f"- {m.get('name', 'Unknown')}: {m.get('value', 'N/A')}" for m in metrics[:15]])
        trends_text = "\n".join([f"- {t}" for t in trends[:10]])
        source_list = "\n".join([f"[{i+1}] {s.get('title', 'Unknown')} ({s.get('url', 'N/A')})" for i, s in enumerate(sources[:15])])
        
        master_instruction = DSMI_STRATEGIC_INTELLIGENCE_PROMPT + """

Respond with JSON:
{{
    "strategic_reasoning": {{
        "causal_chains": [
            "CAUSE [1] -> DIRECT EFFECT -> SECOND-ORDER EFFECT -> THIRD-ORDER EFFECT -> LONG-TERM CONSEQUENCE"
        ],
        "recommendation_answers": {{
            "why_is_this_happening": "...",
            "why_now": "...",
            "market_forces": "...",
            "what_happens_next": "...",
            "if_trends_continue": "...",
            "what_could_disrupt": "..."
        }}
    }},
    "strategic_drivers": [
        {{
            "name": "Driver name",
            "category": "Macroeconomic | Market | Industry | Company",
            "impact_level": "Low | Medium | High",
            "direction": "Positive | Negative | Neutral",
            "expected_duration": "Short | Medium | Long Term",
            "rationale": "Why [1]"
        }}
    ],
    "valuation_analysis": {{
        "status": "Applicable | N/A",
        "metrics": {{
            "P/E": "value", "ROE": "value", "Forward P/E": "value", "Revenue CAGR": "value"
        }},
        "valuation_verdict": "Undervalued | Fairly Valued | Overvalued | Significantly Overvalued | N/A",
        "justification": "Can future growth justify current valuation? Evidence."
    }},
    "scenario_forecasts": {{
        "enabled": true,
        "unit": "unit (USD, %, etc)",
        "time_horizons": ["2026", "2030", "2035"],
        "scenarios": {{
            "bull": {{
                "label": "Bull Case", "probability": "25%", "catalysts": "...",
                "values": {{"2026": "val", "2030": "val"}},
                "strategic_outcome_matrix": {{"revenue": "High", "profit": "High", "market_share": "Gain", "risk_level": "Medium"}}
            }},
            "base": {{
                "label": "Base Case", "probability": "50%", "catalysts": "...",
                "values": {{"2026": "val", "2030": "val"}},
                "strategic_outcome_matrix": {{"revenue": "Medium", "profit": "Medium", "market_share": "Maintain", "risk_level": "Low"}}
            }},
            "bear": {{
                "label": "Bear Case", "probability": "25%", "risks": "...",
                "values": {{"2026": "val", "2030": "val"}},
                "strategic_outcome_matrix": {{"revenue": "Decline", "profit": "Decline", "market_share": "Loss", "risk_level": "High"}}
            }}
        }}
    }},
    "contrarian_intelligence": {{
        "bull_case": "Optimistic perspective",
        "bear_case": "Pessimistic perspective",
        "neutral_case": "Base perspective",
        "independent_judge_assessment": "Unbiased evaluation of all sides",
        "stress_test_scenarios": [
            {{"scenario": "Description", "probability": "Low", "impact": "High", "warning_indicators": "...", "potential_mitigation": "..."}}
        ]
    }},
    "strategic_score": {{
        "overall_score_100": 85,
        "overall_score_10": 8.5,
        "breakdown": {{"Business Quality": 9, "Valuation": 7, "Growth Potential": 8, "Risk": 6, "Competitive Advantage": 8}}
    }},
    "confidence_calibration": {{
        "score_100": 84,
        "source_count": 14,
        "source_agreement": 78,
        "freshness_score": 85,
        "reasoning": "...",
        "supporting_factors": ["Factor 1"],
        "reducing_factors": ["Factor 1"]
    }},
    "investment_thesis": {{
        "why_this_opportunity": "...",
        "why_now": "...",
        "expected_upside": "...",
        "expected_downside": "...",
        "major_catalyst": "...",
        "major_risk": "...",
        "what_invalidates_thesis": "...",
        "alternative_opportunities": "..."
    }},
    "executive_recommendations": {{
        "top_recommendations": [
            {{"priority_level": "High", "expected_impact": "...", "risk_level": "Medium", "recommended_action": "...", "time_horizon": "Short-term"}}
        ]
    }}
}}"""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", master_instruction),
            ("human", f"""Research Question: "{query}"\n\nResearch Summary:\n{truncate_for_llm(research_summary, 3000)}\n\nAnalysis Summary:\n{truncate_for_llm(analysis_summary, 3000)}\n\nKey Metrics:\n{metrics_text}\n\nTrends:\n{trends_text}\n\nNumbered Sources:\n{source_list}\n\nGenerate all required strategic intelligence.""")
        ])
        
        try:
            llm = get_llm(model=self.model, temperature=0.3).bind(response_mime_type="application/json")
            chain = prompt | llm
            response = chain.invoke({"query": query})
            result = safe_parse_json(response.content, fallback={})
        except Exception as e:
            print(f"   ⚠️ Strategic Intelligence chain error: {e}")
            result = {}
        
        return result

def strategic_intelligence_node(state: dict) -> dict:
    try:
        query = state["original_query"]
        research_summary = state.get("research_summary", "")
        metrics = state.get("metrics", [])
        trends = state.get("trends", [])
        comparisons = state.get("comparisons", [])
        analysis_summary = state.get("analysis_summary", "")
        sources = state.get("sources", [])
        
        if not analysis_summary:
            print("   ⚠️ Strategic Intelligence: No data analysis to process")
            return {"status": "Skipped"}
        
        print(f"\n🧠 Strategic Intelligence: Synthesizing insights...")
        agent = StrategicIntelligenceAgent()
        result = agent.analyze(query, research_summary, metrics, trends, comparisons, analysis_summary, sources)
        
        return {
            "strategic_reasoning": result.get("strategic_reasoning", {}),
            "strategic_drivers": result.get("strategic_drivers", []),
            "valuation_analysis": result.get("valuation_analysis", {}),
            "scenario_forecasts": result.get("scenario_forecasts", {}),
            "contrarian_intelligence": result.get("contrarian_intelligence", {}),
            "strategic_score": result.get("strategic_score", {}),
            "confidence_calibration": result.get("confidence_calibration", {}),
            "investment_thesis": result.get("investment_thesis", {}),
            "executive_recommendations": result.get("executive_recommendations", {}),
            "status": f"Strategic intelligence generated."
        }
    except Exception as e:
        print(f"   ❌ Strategic Intelligence error: {e}")
        return {"status": "Failed."}
