"""
Planner Agent - Breaks complex research queries into sub-tasks.
The "Chief Strategist" — first agent in the graph.

Migration: Uses LangChain ChatPromptTemplate + structured output via LLM.
"""
from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from utils.llm_client import get_llm, call_llm_json
from utils.prompts import DSMI_V2_MASTER_PROMPT


class PlannerAgent:
    """
    Decomposes a user's high-level research question into 4-7 specific,
    actionable sub-tasks with priorities and search queries.
    """
    
    def __init__(self, model: str = "gemini-2.0-flash"):
        self.model = model
    
    def plan(self, query: str) -> Dict[str, Any]:
        """
        Break a research question into sub-tasks.
        
        Args:
            query: The user's original research question
            
        Returns:
            Dict with 'plan' (description) and 'sub_tasks' (list of task dicts)
        """
        # Detect query intent: pricing/forecast vs. general market analysis
        price_keywords = ["price", "cost", "valuation", "forecast", "prediction", "predict",
                          "worth", "value", "how much", "pricing", "rate", "per ounce",
                          "per kg", "per gram", "$/oz", "usd"]
        query_lower = query.lower()
        is_price_query = any(kw in query_lower for kw in price_keywords)
        
        if is_price_query:
            mandatory_categories = """MANDATORY: The query is about PRICING/VALUATION/FORECASTING. Your sub-tasks MUST include at least one from EACH:
1. price_forecasts — "Search for specific price forecasts and projections in USD (e.g., gold price forecast 2030 2040 2050 per ounce)"
2. historical_prices — "Search for historical price data, trends over last 10-20 years, price charts"
3. macroeconomic_drivers — "Search for factors that drive price: inflation rates, interest rates, USD index, central bank policy, supply-demand balance"
4. competitive_landscape — Top companies, producers, market share, recent M&A activity
5. risks — Geopolitical risks, regulatory changes, alternative investments, market threats

OPTIONAL additional categories:
- investment_activity — VC funding, M&A deals, ETF flows
- supply_demand — Production volumes, mining output, consumption patterns
- technology — Tech advancements affecting production or demand
- sentiment — Investor sentiment, analyst consensus, market positioning

CRITICAL: The user is asking about PRICE (in currency units like USD, EUR, etc.), NOT about market size in volume units (kilotons, tonnes). Make sure your search queries explicitly include words like "price forecast", "price prediction", "USD per ounce", "price outlook" etc."""
        else:
            mandatory_categories = """MANDATORY: Your sub-tasks MUST include at least one task from EACH of these categories:
1. market_size — Current and projected market sizes, revenue, CAGR
2. competitive_landscape — Top companies, market share, key players, recent M&A activity
3. trends — Emerging technology trends, adoption patterns, industry shifts
4. risks — Regulatory risks, market threats, disruption potential
5. investment_activity — VC funding trends, M&A deals, startup ecosystem

OPTIONAL additional categories (include if relevant):
- talent_demand — Job market trends, skill requirements, salary data
- technology — Specific tech advancements driving the sector
- policy — Government regulations, policies affecting the industry
- case_studies — Success stories, failures, lessons learned"""

        # Build LangChain prompt template
        system_msg = DSMI_V2_MASTER_PROMPT + """

You are the Chief Research Strategist (Planner) at a top consulting firm.
Your job is to break down a complex research question into a structured research plan and 5-8 specific, actionable sub-tasks.

RULE #1: ANSWER THE ACTUAL QUESTION. Determine the Question Type, Decision Type, and Expected Output Type.
RULE #2: RESEARCH PLANNING FIRST. You must formulate the Research Objective, Key Questions, Required Evidence, Critical Variables, Scope, and Knowledge Gaps.

Each sub-task should:
- Be a focused, searchable question
- Have a clear priority (1=most important, 5=least)
- Cover a DIFFERENT angle of the main question

{mandatory_categories}

Respond with JSON:
{{
    "plan": "A detailed 3-5 sentence description of the research methodology",
    "research_objective": "Clear statement of what we are trying to achieve",
    "key_questions": ["Question 1", "Question 2"],
    "required_evidence": ["Evidence 1", "Evidence 2"],
    "critical_variables": ["Variable 1", "Variable 2"],
    "research_scope": "Scope boundaries",
    "knowledge_gaps": ["Gap 1", "Gap 2"],
    "sub_tasks": [
        {{
            "id": 1,
            "query": "Specific search query for this sub-task",
            "priority": 1,
            "category": "price_forecasts | historical_prices | macroeconomic_drivers | market_size | competitive_landscape | trends | risks | investment_activity | supply_demand | technology | sentiment | talent_demand | policy | case_studies"
        }}
    ]
}}"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_msg),
            ("human", "Break down this research question into comprehensive sub-tasks:\n\n\"{query}\"")
        ])
        
        # Get LLM and create chain
        llm = get_llm(model=self.model, temperature=0.4)
        chain = prompt | llm
        
        # Invoke the chain
        try:
            response = chain.invoke({"query": query, "mandatory_categories": mandatory_categories})
            from utils.llm_client import safe_parse_json
            result = safe_parse_json(
                response.content,
                fallback={
                    "plan": f"Research plan for: {query}",
                    "sub_tasks": [
                        {"id": 1, "query": query, "priority": 1, "category": "general"}
                    ]
                }
            )
        except Exception as e:
            print(f"   ⚠️ Planner chain error: {e}")
            result = {
                "plan": f"Research plan for: {query}",
                "sub_tasks": [
                    {"id": 1, "query": query, "priority": 1, "category": "general"}
                ]
            }
        
        # Validate and normalize sub_tasks
        sub_tasks = result.get("sub_tasks", [])
        if not sub_tasks:
            sub_tasks = [{"id": 1, "query": query, "priority": 1, "category": "general"}]
        
        # Ensure each task has required fields
        for i, task in enumerate(sub_tasks):
            task.setdefault("id", i + 1)
            task.setdefault("priority", 1)
            task.setdefault("status", "pending")
            task.setdefault("category", "general")
        
        # Sort by priority
        sub_tasks.sort(key=lambda t: t.get("priority", 5))
        
        # Build comprehensive plan string from the new fields
        plan_desc = result.get("plan", f"Research plan for: {query}")
        objective = result.get("research_objective", "")
        if objective:
            plan_desc += f"\n\n**Objective:** {objective}"
            plan_desc += f"\n**Key Questions:** {', '.join(result.get('key_questions', []))}"
            plan_desc += f"\n**Required Evidence:** {', '.join(result.get('required_evidence', []))}"
            plan_desc += f"\n**Critical Variables:** {', '.join(result.get('critical_variables', []))}"
            plan_desc += f"\n**Scope:** {result.get('research_scope', '')}"
            plan_desc += f"\n**Knowledge Gaps:** {', '.join(result.get('knowledge_gaps', []))}"

        return {
            "plan": plan_desc,
            "sub_tasks": sub_tasks
        }


def planner_node(state: dict) -> dict:
    """
    LangGraph node function for the Planner agent.
    Reads: original_query
    Writes: sub_tasks, research_plan, status
    """
    try:
        query = state["original_query"]
        print(f"\n🧠 Planner: Breaking down query...")
        
        planner = PlannerAgent()
        result = planner.plan(query)
        
        print(f"   📋 Created {len(result['sub_tasks'])} sub-tasks")
        for task in result["sub_tasks"]:
            print(f"      [{task.get('priority', '?')}] {task['query'][:60]}...")
        
        return {
            "sub_tasks": result["sub_tasks"],
            "research_plan": result["plan"],
            "status": f"Planning complete. {len(result['sub_tasks'])} sub-tasks created.",
        }
    except Exception as e:
        print(f"   ❌ Planner error: {e}")
        return {
            "sub_tasks": [{"id": 1, "query": state["original_query"], "priority": 1, "status": "pending"}],
            "research_plan": f"Fallback: Direct research on {state['original_query']}",
            "error_log": [f"Planner error: {str(e)}"],
            "status": "Planning failed, using direct research.",
        }
