"""
Data Analyst Agent - Extracts metrics, trends, and structured data from research.
"""
from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from utils.llm_client import get_llm, safe_parse_json, truncate_for_llm
from utils.prompts import DSMI_DATA_ANALYST_PROMPT

class DataAnalystAgent:
    def __init__(self, model: str = "gemini-2.0-flash"):
        self.model = model
    
    def analyze(self, query: str, research_content: List[Dict], sources: List[Dict]) -> Dict[str, Any]:
        content_text = "\n\n".join([
            f"Source: {c.get('title', 'Unknown')}\n"
            f"URL: {c.get('url', 'N/A')}\n"
            f"Content: {truncate_for_llm(c.get('content', ''), max_chars=3000)}"
            for c in research_content[:10]
        ])
        content_text = truncate_for_llm(content_text, max_chars=12000)
        source_list = "\n".join([f"[{i+1}] {s.get('title', 'Unknown')} ({s.get('url', 'N/A')})" for i, s in enumerate(sources[:15])])
        
        master_instruction = DSMI_DATA_ANALYST_PROMPT + """

Respond with JSON:
{{
    "metrics": [
        {{
            "name": "metric name",
            "value": "the value",
            "year": "year if available",
            "source": "full source name",
            "confidence": 0.82
        }}
    ],
    "trends": ["Trend 1 with citation [1]", "Trend 2 with citation [2]"],
    "comparisons": [
        {{
            "category": "comparison category",
            "items": [
                {{"name": "Item A", "details": "details [1]"}},
                {{"name": "Item B", "details": "details [2]"}}
            ]
        }}
    ],
    "charts_data": [
        {{
            "type": "bar",
            "title": "Chart title",
            "x_label": "X axis label",
            "y_label": "Y axis label",
            "data": [{{"x": "Category A", "y": 45.2}}]
        }}
    ],
    "analysis_summary": "5+ paragraph deep synthesis with inline citations [1][2]."
}}

CHART TYPES AVAILABLE: bar, line, pie, radar
Generate at least 2 charts comparing key dimensions of the research topic."""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", master_instruction),
            ("human", "Research Question: \"{query}\"\n\nResearch Content:\n{content_text}\n\nNumbered Sources (use these numbers for inline citations [1], [2], etc.):\n{source_list}\n\nExtract all metrics, real trends, comparisons, chart data, and write a deep analysis summary with inline citations.")
        ])
        
        try:
            llm = get_llm(model=self.model, temperature=0.2).bind(response_mime_type="application/json")
            chain = prompt | llm
            response = chain.invoke({"query": query, "content_text": content_text, "source_list": source_list})
            result = safe_parse_json(response.content, fallback={"metrics": [], "trends": [], "comparisons": [], "charts_data": [], "analysis_summary": "Analysis failed."})
        except Exception as e:
            print(f"   ⚠️ Data Analysis chain error: {e}")
            result = {"metrics": [], "trends": [], "comparisons": [], "charts_data": [], "analysis_summary": "Analysis failed."}
        
        return result

def data_analyst_node(state: dict) -> dict:
    try:
        query = state["original_query"]
        raw_content = state.get("raw_content", [])
        sources = state.get("sources", [])
        
        if not raw_content:
            print("   ⚠️ Data Analyst: No content to analyze")
            return {"metrics": [], "trends": [], "charts_data": [], "comparisons": [], "analysis_summary": "No content.", "status": "Skipped"}
        
        print(f"\n📊 Data Analyst: Analyzing {len(raw_content)} sources...")
        analyst = DataAnalystAgent()
        result = analyst.analyze(query, raw_content, sources)
        
        return {
            "metrics": result.get("metrics", []),
            "trends": result.get("trends", []),
            "charts_data": result.get("charts_data", []),
            "comparisons": result.get("comparisons", []),
            "analysis_summary": result.get("analysis_summary", ""),
            "status": f"Data extracted: {len(result.get('metrics', []))} metrics."
        }
    except Exception as e:
        print(f"   ❌ Data Analyst error: {e}")
        return {"metrics": [], "trends": [], "charts_data": [], "comparisons": [], "analysis_summary": "Error.", "status": "Failed."}
