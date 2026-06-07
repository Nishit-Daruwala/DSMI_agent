"""
Publisher Agent - Generates the final research report.
The "Report Writer" — compiles everything into a professional, downloadable report.

Migration: Uses LangChain ChatPromptTemplate + chain invocation.
"""
from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from utils.llm_client import get_llm, safe_parse_json, truncate_for_llm
from utils.prompts import DSMI_V2_MASTER_PROMPT


class PublisherAgent:
    """
    Compiles all research, analysis, and metrics into a comprehensive
    markdown report with:
    - Executive Summary (high-level strategic narrative)
    - Strategic Recommendations (direct verdict + actionable advice)
    - Detailed Findings (deep-dive analysis, NOT a copy of exec summary)
    - SWOT Analysis
    - Data Tables
    - Source Citations
    """
    
    def __init__(self, model: str = "gemini-2.0-flash"):
        self.model = model
    
    def generate_report(
        self,
        query: str,
        research_plan: str,
        research_summary: str,
        metrics: List[Dict],
        trends: List[str],
        comparisons: List[Dict],
        analysis_summary: str,
        sources: List[Dict],
        quality_score: float,
        quality_breakdown: Dict,
        warnings: List[str],
        strategic_reasoning: Dict = None,
        strategic_drivers: List[Dict] = None,
        valuation_analysis: Dict = None,
        scenario_forecasts: Dict = None,
        contrarian_intelligence: Dict = None,
        strategic_score: Dict = None,
        confidence_calibration: Dict = None,
        investment_thesis: Dict = None,
        executive_recommendations: Dict = None,
    ) -> Dict[str, Any]:
        """
        Generate the final research report.
        
        Returns:
            Dict with final_report (markdown), executive_summary, swot_analysis, and recommendations
        """
        # Step 1: Generate SWOT analysis
        swot = self._generate_swot(query, analysis_summary, metrics, trends)
        
        # Step 2: Generate executive summary (strategic narrative, NOT data dump)
        exec_summary = self._generate_executive_summary(query, analysis_summary, metrics)
        
        # Step 3: Generate strategic recommendations / verdict
        recommendations = self._generate_recommendations(
            query, analysis_summary, metrics, trends, swot
        )
        
        # Step 4: Generate deep-dive detailed analysis (unique content)
        detailed_analysis = self._generate_detailed_analysis(
            query, research_summary, analysis_summary, metrics, trends, comparisons
        )
        
        # Step 5: Compile the full report
        report = self._compile_report(
            query=query,
            executive_summary=exec_summary,
            research_plan=research_plan,
            research_summary=research_summary,
            metrics=metrics,
            trends=trends,
            comparisons=comparisons,
            detailed_analysis=detailed_analysis,
            recommendations=recommendations,
            swot=swot,
            sources=sources,
            quality_score=quality_score,
            quality_breakdown=quality_breakdown,
            warnings=warnings,
            strategic_reasoning=strategic_reasoning or {},
            strategic_drivers=strategic_drivers or [],
            valuation_analysis=valuation_analysis or {},
            scenario_forecasts=scenario_forecasts or {},
            contrarian_intelligence=contrarian_intelligence or {},
            strategic_score=strategic_score or {},
            confidence_calibration=confidence_calibration or {},
            investment_thesis=investment_thesis or {},
            executive_recommendations=executive_recommendations or {},
        )
        
        return {
            "final_report": report,
            "executive_summary": exec_summary,
            "swot_analysis": swot,
            "recommendations": recommendations,
        }
    
    def _generate_swot(
        self, query: str, analysis: str, metrics: List[Dict], trends: List[str]
    ) -> Dict[str, List[str]]:
        """Generate SWOT analysis from research findings."""
        metrics_text = "\n".join([
            f"- {m.get('name', 'Unknown')}: {m.get('value', 'N/A')}" 
            for m in metrics[:15]
        ])
        trends_text = "\n".join([f"- {t}" for t in trends[:10]])
        
        system_msg = DSMI_V2_MASTER_PROMPT + """

You are a strategy consultant. Generate a SWOT analysis based on research findings.

IMPORTANT: Do NOT restate market size numbers. Focus on strategic insights:
- Strengths: What advantages exist? What makes this sector resilient?
- Weaknesses: What internal challenges or vulnerabilities exist?
- Opportunities: What untapped potential or emerging openings exist?
- Threats: What external risks could derail growth?

Respond with JSON:
{{
    "strengths": ["strength 1", "strength 2", "strength 3"],
    "weaknesses": ["weakness 1", "weakness 2", "weakness 3"],
    "opportunities": ["opportunity 1", "opportunity 2", "opportunity 3"],
    "threats": ["threat 1", "threat 2", "threat 3"]
}}

Each item should be specific, actionable, and insight-driven. Aim for 3-5 items per category.
Do NOT simply repeat market size projections — focus on WHY those numbers matter strategically."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_msg),
            ("human", """Research Topic: "{query}"

Analysis: {analysis}

Key Metrics:
{metrics_text}

Trends:
{trends_text}

Generate a SWOT analysis with strategic insights (not market size restatements).""")
        ])
        
        try:
            llm = get_llm(model=self.model, temperature=0.3)
            llm = llm.bind(response_mime_type="application/json")
            chain = prompt | llm
            response = chain.invoke({
                "query": query,
                "analysis": truncate_for_llm(analysis, 3000),
                "metrics_text": metrics_text,
                "trends_text": trends_text,
            })
            result = safe_parse_json(
                response.content,
                fallback={
                    "strengths": ["Data not available"],
                    "weaknesses": ["Data not available"],
                    "opportunities": ["Data not available"],
                    "threats": ["Data not available"]
                }
            )
        except Exception as e:
            print(f"   ⚠️ SWOT chain error: {e}")
            result = {
                "strengths": ["Data not available"],
                "weaknesses": ["Data not available"],
                "opportunities": ["Data not available"],
                "threats": ["Data not available"]
            }
        
        return {
            "strengths": result.get("strengths", []),
            "weaknesses": result.get("weaknesses", []),
            "opportunities": result.get("opportunities", []),
            "threats": result.get("threats", []),
        }
    
    def _generate_executive_summary(
        self, query: str, analysis: str, metrics: List[Dict]
    ) -> str:
        """Generate a high-level strategic executive summary (NOT a data dump)."""
        metrics_text = "\n".join([
            f"- {m.get('name', 'Unknown')}: {m.get('value', 'N/A')}" 
            for m in metrics[:10]
        ])
        
        system_msg = DSMI_V2_MASTER_PROMPT + """

You are a senior strategy advisor writing for C-level executives.

Write a concise executive summary (3-4 paragraphs) that:
1. Opens with the DIRECT ANSWER to the research question (clear verdict/recommendation)
2. Summarizes the strategic landscape at a high level
3. Highlights 2-3 key implications for decision-makers
4. Closes with a forward-looking statement

RULES:
- Lead with the answer, not the methodology
- Reference key numbers SPARINGLY (1-2 max per paragraph) to support claims
- Do NOT list every metric — that belongs in the data section
- Use confident, decisive language ("Our analysis indicates..." not "The data shows...")
- Do NOT use markdown headers, bullet points, or formatting in the summary
- Write in flowing professional prose"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_msg),
            ("human", """Research Question: "{query}"

Analysis: {analysis}

Key Metrics:
{metrics_text}

Write the executive summary. Start with the direct answer to the question.""")
        ])
        
        try:
            llm = get_llm(model=self.model, temperature=0.3)
            chain = prompt | llm
            response = chain.invoke({
                "query": query,
                "analysis": truncate_for_llm(analysis, 4000),
                "metrics_text": metrics_text,
            })
            return response.content
        except Exception as e:
            print(f"   ⚠️ Executive summary chain error: {e}")
            return analysis[:500] if analysis else "Executive summary generation failed."
    
    def _generate_recommendations(
        self,
        query: str,
        analysis: str,
        metrics: List[Dict],
        trends: List[str],
        swot: Dict[str, List[str]],
    ) -> Dict[str, Any]:
        """
        Generate strategic recommendations with a clear verdict.
        This is the core value-add — the section that ANSWERS the user's question.
        """
        metrics_text = "\n".join([
            f"- {m.get('name', 'Unknown')}: {m.get('value', 'N/A')}"
            for m in metrics[:15]
        ])
        trends_text = "\n".join([f"- {t}" for t in trends[:10]])
        swot_text = (
            f"Strengths: {', '.join(swot.get('strengths', []))}\n"
            f"Weaknesses: {', '.join(swot.get('weaknesses', []))}\n"
            f"Opportunities: {', '.join(swot.get('opportunities', []))}\n"
            f"Threats: {', '.join(swot.get('threats', []))}"
        )

        system_msg = DSMI_V2_MASTER_PROMPT + """

You are a senior strategy consultant delivering final recommendations to a client.

Your job is to provide:
1. A CLEAR VERDICT that directly answers the research question
2. Ranked recommendations with justification
3. Risk-adjusted advice for different stakeholder types
4. An Investment/Business Thesis (RULE #12) answering: Why this? Why now? Expected upside? Expected downside? Major catalyst? Key risk?

Respond with JSON:
{{
    "verdict": "A single, clear 2-3 sentence answer to the research question. Be decisive — pick a winner if the question asks for one.",
    "primary_recommendation": "The #1 recommended action with specific justification",
    "ranked_options": [
        {{
            "rank": 1,
            "option": "Option name",
            "rationale": "Why this ranks #1 (cite specific metrics)",
            "risk_level": "Low/Medium/High",
            "time_horizon": "Short-term/Medium-term/Long-term"
        }}
    ],
    "stakeholder_advice": {{
        "enterprises": "What large enterprises should do",
        "startups": "What startups and new entrants should do",
        "investors": "What investors should consider",
        "professionals": "What individual professionals should focus on"
    }},
    "thesis": "Investment/Business Thesis (Why this? Why now? Catalysts? Risks? Upside/Downside?)",
    "key_risks": ["Risk 1 with mitigation suggestion", "Risk 2 with mitigation suggestion"],
    "timeline": "When to act and key milestones to watch"
}}

Be DECISIVE. Clients pay for opinions backed by data, not hedging."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_msg),
            ("human", """Research Question: "{query}"

Analysis Summary: {analysis}

Key Metrics:
{metrics_text}

Trends:
{trends_text}

SWOT:
{swot_text}

Provide your verdict and ranked recommendations.""")
        ])

        try:
            llm = get_llm(model=self.model, temperature=0.4)
            llm = llm.bind(response_mime_type="application/json")
            chain = prompt | llm
            response = chain.invoke({
                "query": query,
                "analysis": truncate_for_llm(analysis, 3000),
                "metrics_text": metrics_text,
                "trends_text": trends_text,
                "swot_text": swot_text,
            })
            result = safe_parse_json(
                response.content,
                fallback={
                    "verdict": "Insufficient data to make a definitive recommendation.",
                    "primary_recommendation": "Gather more data before committing.",
                    "ranked_options": [],
                    "stakeholder_advice": {},
                    "key_risks": [],
                    "timeline": "Not enough data to project timeline.",
                }
            )
        except Exception as e:
            print(f"   ⚠️ Recommendations chain error: {e}")
            result = {
                "verdict": "Recommendation generation failed.",
                "primary_recommendation": "Unable to generate recommendations.",
                "ranked_options": [],
                "stakeholder_advice": {},
                "key_risks": [],
                "timeline": "",
            }

        return result

    def _generate_detailed_analysis(
        self,
        query: str,
        research_summary: str,
        analysis_summary: str,
        metrics: List[Dict],
        trends: List[str],
        comparisons: List[Dict],
    ) -> str:
        """
        Generate a deep-dive detailed analysis that is UNIQUE from the executive summary.
        This should be 5-10 paragraphs with sub-sections, comparisons, and depth.
        """
        metrics_text = "\n".join([
            f"- {m.get('name', 'Unknown')}: {m.get('value', 'N/A')} (Source: {m.get('source', 'N/A')})"
            for m in metrics[:20]
        ])
        trends_text = "\n".join([f"- {t}" for t in trends[:10]])
        comparisons_text = ""
        if comparisons:
            for comp in comparisons[:5]:
                comparisons_text += f"\nCategory: {comp.get('category', 'N/A')}\n"
                for item in comp.get('items', []):
                    comparisons_text += f"  - {item.get('name', '')}: {item.get('details', '')}\n"

        system_msg = DSMI_V2_MASTER_PROMPT + """

You are a senior market research analyst writing the DETAILED FINDINGS section of a research report.

This section is DIFFERENT from the Executive Summary. It must provide:
1. A structured breakdown with clear sub-headings (use ### for sub-sections)
2. Segment-by-segment or niche-by-niche analysis with comparisons
3. Year-over-year or period-over-period growth analysis where data is available
4. Geographic or demographic breakdowns if relevant
5. Competitive dynamics and market structure analysis
6. Technology adoption curves and maturity assessments

RULES:
- Write 800-1500 words minimum
- Use markdown sub-headings (###) to organize into logical sections
- Include specific numbers from the metrics with proper attribution
- Compare and contrast different segments/options against each other
- DO NOT repeat the executive summary — go DEEPER
- Add analytical commentary explaining WHY numbers are what they are
- Include comparison tables where appropriate using markdown tables"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_msg),
            ("human", """Research Question: "{query}"

Research Summary:
{research_summary}

Analysis Summary:
{analysis_summary}

Key Metrics:
{metrics_text}

Trends:
{trends_text}

Comparisons:
{comparisons_text}

Write the detailed analysis with sub-sections. Go deep — this is the core analytical section.""")
        ])

        try:
            llm = get_llm(model=self.model, temperature=0.3)
            chain = prompt | llm
            response = chain.invoke({
                "query": query,
                "research_summary": truncate_for_llm(research_summary, 4000),
                "analysis_summary": truncate_for_llm(analysis_summary, 3000),
                "metrics_text": metrics_text,
                "trends_text": trends_text,
                "comparisons_text": comparisons_text,
            })
            return response.content
        except Exception as e:
            print(f"   ⚠️ Detailed analysis chain error: {e}")
            return analysis_summary if analysis_summary else "Detailed analysis generation failed."

    def _compile_report(self, **kwargs) -> str:
        """Compile all sections into a formatted markdown report."""
        query = kwargs["query"]
        exec_summary = kwargs["executive_summary"]
        research_plan = kwargs["research_plan"]
        detailed_analysis = kwargs["detailed_analysis"]
        metrics = kwargs["metrics"]
        trends = kwargs["trends"]
        comparisons = kwargs["comparisons"]
        recommendations = kwargs["recommendations"]
        swot = kwargs["swot"]
        sources = kwargs["sources"]
        quality_score = kwargs["quality_score"]
        quality_breakdown = kwargs["quality_breakdown"]
        warnings = kwargs.get("warnings", [])
        strategic_reasoning = kwargs.get("strategic_reasoning", {})
        strategic_drivers = kwargs.get("strategic_drivers", [])
        valuation_analysis = kwargs.get("valuation_analysis", {})
        scenario_forecasts = kwargs.get("scenario_forecasts", {})
        contrarian_intelligence = kwargs.get("contrarian_intelligence", {})
        strategic_score = kwargs.get("strategic_score", {})
        confidence_calibration = kwargs.get("confidence_calibration", {})
        investment_thesis = kwargs.get("investment_thesis", {})
        executive_recommendations = kwargs.get("executive_recommendations", {})
        
        # Build metrics table with Year column and deduplication
        metrics_table = ""
        if metrics:
            metrics_table = "| Metric | Value | Year | Source | Confidence |\n|--------|-------|------|--------|------------|\n"
            seen_metrics = set()
            for m in metrics:
                name = m.get("name", "Unknown")
                value = m.get("value", "N/A")
                year = m.get("year", "—")
                source = m.get("source", "Research")
                conf = m.get("confidence", "N/A")
                
                # Dedup key: name + value
                dedup_key = f"{name}|{value}"
                if dedup_key in seen_metrics:
                    continue
                seen_metrics.add(dedup_key)
                
                # Format confidence
                if isinstance(conf, (int, float)):
                    conf_pct = conf if conf <= 1 else conf / 100
                    bar_len = int(conf_pct * 5)
                    conf = "█" * bar_len + "░" * (5 - bar_len) + f" {conf_pct:.0%}"
                
                metrics_table += f"| {name} | {value} | {year} | {source} | {conf} |\n"
        
        # Build trends list
        trends_section = ""
        if trends:
            trends_section = "\n".join([f"- {t}" for t in trends])
        
        # Build SWOT as clean bullet lists (NOT broken markdown table)
        swot_section = ""
        if swot:
            strengths = "\n".join([f"  - {s}" for s in swot.get('strengths', [])])
            weaknesses = "\n".join([f"  - {w}" for w in swot.get('weaknesses', [])])
            opportunities = "\n".join([f"  - {o}" for o in swot.get('opportunities', [])])
            threats = "\n".join([f"  - {t}" for t in swot.get('threats', [])])
            
            swot_section = f"""### 💪 Strengths
{strengths}

### ⚠️ Weaknesses
{weaknesses}

### 🚀 Opportunities
{opportunities}

### 🔥 Threats
{threats}"""

        # Build recommendations section
        rec_section = ""
        if recommendations:
            verdict = recommendations.get("verdict", "")
            primary = recommendations.get("primary_recommendation", "")
            
            rec_section = f"""> **🎯 Verdict:** {verdict}

**Primary Recommendation:** {primary}
"""
            # Thesis
            thesis = recommendations.get("thesis", "")
            if thesis:
                rec_section += f"\n### 💡 Investment / Business Thesis\n\n{thesis}\n\n"

            # Ranked options
            ranked = recommendations.get("ranked_options", [])
            if ranked:
                rec_section += "\n### Ranked Options\n\n"
                rec_section += "| Rank | Option | Risk Level | Time Horizon |\n|------|--------|------------|-------------|\n"
                for opt in ranked:
                    rec_section += f"| #{opt.get('rank', '—')} | **{opt.get('option', '')}** | {opt.get('risk_level', '—')} | {opt.get('time_horizon', '—')} |\n"
                rec_section += "\n"
                for opt in ranked:
                    rec_section += f"**#{opt.get('rank', '')} — {opt.get('option', '')}:** {opt.get('rationale', '')}\n\n"
            
            # Stakeholder advice
            advice = recommendations.get("stakeholder_advice", {})
            if advice:
                rec_section += "### Who Should Do What\n\n"
                labels = {
                    "enterprises": "🏢 Enterprises",
                    "startups": "🚀 Startups & New Entrants",
                    "investors": "💰 Investors",
                    "professionals": "👤 Professionals",
                }
                for key, label in labels.items():
                    if advice.get(key):
                        rec_section += f"- **{label}:** {advice[key]}\n"
            
            # Key risks
            risks = recommendations.get("key_risks", [])
            if risks:
                rec_section += "\n### Key Risks to Monitor\n\n"
                for risk in risks:
                    rec_section += f"- ⚠️ {risk}\n"
            
            # Timeline
            timeline = recommendations.get("timeline", "")
            if timeline:
                rec_section += f"\n### Timeline\n\n{timeline}\n"

        # Build sources list
        sources_section = ""
        if sources:
            sources_section = "\n".join([
                f"{i+1}. [{s.get('title', 'Source')}]({s.get('url', '#')})"
                for i, s in enumerate(sources)
            ])
        
        # Build quality report
        quality_section = f"**Overall Score: {quality_score:.0%}**\n\n"
        if quality_breakdown:
            quality_section += "| Dimension | Score |\n|-----------|-------|\n"
            for dim, score in quality_breakdown.items():
                bar = "█" * int(float(score) * 10) + "░" * (10 - int(float(score) * 10))
                quality_section += f"| {dim.replace('_', ' ').title()} | {bar} {float(score):.0%} |\n"
        
        # Strategic Reasoning Section
        reasoning_section = ""
        if strategic_reasoning:
            reasoning_section = "## 🧠 Strategic Reasoning\n\n"
            chains = strategic_reasoning.get("causal_chains", [])
            if chains:
                reasoning_section += "### Causal Chains\n\n"
                for chain in chains:
                    reasoning_section += f"> {chain}\n\n"
            
            answers = strategic_reasoning.get("recommendation_answers", {})
            if answers:
                reasoning_section += "### Core Analysis\n\n"
                if answers.get("why_is_this_happening"): reasoning_section += f"- **Why is this happening?** {answers['why_is_this_happening']}\n"
                if answers.get("why_now"): reasoning_section += f"- **Why now?** {answers['why_now']}\n"
                if answers.get("market_forces"): reasoning_section += f"- **Market forces:** {answers['market_forces']}\n"
                if answers.get("what_happens_next"): reasoning_section += f"- **What happens next?** {answers['what_happens_next']}\n"
                if answers.get("if_trends_continue"): reasoning_section += f"- **If trends continue:** {answers['if_trends_continue']}\n"
                if answers.get("what_could_disrupt"): reasoning_section += f"- **Potential disruptions:** {answers['what_could_disrupt']}\n"
            reasoning_section += "\n---\n\n"

        # Strategic Drivers Section
        drivers_section = ""
        if strategic_drivers:
            drivers_section = "## 🌍 Strategic Drivers\n\n"
            drivers_section += "| Driver | Category | Impact | Direction | Duration | Rationale |\n"
            drivers_section += "|--------|----------|--------|-----------|----------|-----------|\n"
            for d in strategic_drivers:
                drivers_section += f"| **{d.get('name','')}** | {d.get('category','')} | {d.get('impact_level','')} | {d.get('direction','')} | {d.get('expected_duration','')} | {d.get('rationale','')} |\n"
            drivers_section += "\n---\n\n"

        # Valuation Analysis Section
        valuation_section = ""
        if valuation_analysis and valuation_analysis.get("status") != "N/A":
            valuation_section = "## 💰 Valuation Analysis\n\n"
            valuation_section += f"> **Valuation Verdict:** {valuation_analysis.get('valuation_verdict', 'N/A')}\n\n"
            metrics_dict = valuation_analysis.get("metrics", {})
            if metrics_dict:
                valuation_section += "| Metric | Value |\n|--------|-------|\n"
                for k, v in metrics_dict.items():
                    valuation_section += f"| {k} | {v} |\n"
            justification = valuation_analysis.get("justification", "")
            if justification:
                valuation_section += f"\n**Justification:** {justification}\n"
            valuation_section += "\n---\n\n"

        # 8. Risk Assessment
        risk_section = "## 8. Risk Assessment\n\n"
        if warnings:
            risk_section += "> [!WARNING]\n> **Warnings:**\n" + "\n".join([f"> - {w}" for w in warnings]) + "\n\n"
        # Can pull risks from contrarian stress test
        stress_tests = contrarian_intelligence.get("stress_test_scenarios", [])
        if stress_tests:
            risk_section += "### Top Failure Scenarios\n\n"
            risk_section += "| Failure Scenario | Probability | Impact | Warning Indicators | Mitigation |\n|------------------|-------------|--------|--------------------|------------|\n"
            for test in stress_tests:
                risk_section += f"| {test.get('scenario','')} | {test.get('probability','')} | {test.get('impact','')} | {test.get('warning_indicators','')} | {test.get('potential_mitigation', '')} |\n"
            risk_section += "\n"

        # 9. Investment / Business Thesis
        thesis_section = "## 9. Investment / Business Thesis\n\n"
        if investment_thesis:
            thesis_section += f"- **Why this opportunity?** {investment_thesis.get('why_this_opportunity', '—')}\n"
            thesis_section += f"- **Why now?** {investment_thesis.get('why_now', '—')}\n"
            thesis_section += f"- **Expected Upside:** {investment_thesis.get('expected_upside', '—')}\n"
            thesis_section += f"- **Expected Downside:** {investment_thesis.get('expected_downside', '—')}\n"
            thesis_section += f"- **Major Catalyst:** {investment_thesis.get('major_catalyst', '—')}\n"
            thesis_section += f"- **Major Risk:** {investment_thesis.get('major_risk', '—')}\n"
            thesis_section += f"- **What invalidates thesis?** {investment_thesis.get('what_invalidates_thesis', '—')}\n"
            thesis_section += f"- **Alternative opportunities:** {investment_thesis.get('alternative_opportunities', '—')}\n\n"
        else:
            thesis_section += "*Thesis not provided.*\n\n"

        # 12. Executive Recommendations
        exec_rec_section = "## 12. Executive Recommendations\n\n"
        if executive_recommendations and executive_recommendations.get("top_recommendations"):
            exec_rec_section += "| Priority | Action | Impact | Risk | Horizon |\n|----------|--------|--------|------|---------|\n"
            for rec in executive_recommendations.get("top_recommendations", []):
                exec_rec_section += f"| {rec.get('priority_level','')} | {rec.get('recommended_action','')} | {rec.get('expected_impact','')} | {rec.get('risk_level','')} | {rec.get('time_horizon','')} |\n"
            exec_rec_section += "\n"
        else:
            # Fallback to older recommendation format if new format is missing
            exec_rec_section += rec_section if rec_section else "*No recommendations provided.*\n\n"

        # 6. Contrarian Intelligence
        contrarian_section = "## 6. Contrarian Intelligence\n\n"
        if contrarian_intelligence:
            if contrarian_intelligence.get("bull_case"): contrarian_section += f"**Bull Case:** {contrarian_intelligence['bull_case']}\n\n"
            if contrarian_intelligence.get("bear_case"): contrarian_section += f"**Bear Case:** {contrarian_intelligence['bear_case']}\n\n"
            if contrarian_intelligence.get("neutral_case"): contrarian_section += f"**Neutral Case:** {contrarian_intelligence['neutral_case']}\n\n"
            if contrarian_intelligence.get("independent_judge_assessment"): contrarian_section += f"**Independent Judge:** {contrarian_intelligence['independent_judge_assessment']}\n\n"
        else:
            contrarian_section += "*Contrarian intelligence not provided.*\n\n"

        # 7. Scenario Analysis
        scenario_section = "## 7. Scenario Analysis\n\n"
        if scenario_forecasts and scenario_forecasts.get("enabled"):
            unit = scenario_forecasts.get("unit", "")
            scenario_section += f"**Unit:** {unit}\n\n"
            scenarios = scenario_forecasts.get("scenarios", {})
            for case, data in scenarios.items():
                scenario_section += f"### {data.get('label', case.title())} ({data.get('probability', 'N/A')})\n"
                scenario_section += f"**Catalysts/Risks:** {data.get('catalysts', data.get('risks', '—'))}\n\n"
                
                vals = data.get('values', {})
                if vals:
                    scenario_section += "| Year | Forecast |\n|------|----------|\n"
                    for yr, val in vals.items():
                        scenario_section += f"| {yr} | {val} |\n"
                scenario_section += "\n"
        else:
            scenario_section += "*Scenario analysis not provided.*\n\n"

        # 10. Strategic Score
        score_section = "## 10. Strategic Score\n\n"
        if strategic_score:
            score_section += f"**Overall Score:** {strategic_score.get('overall_score_100', 'N/A')}/100\n\n"
            bd = strategic_score.get("breakdown", {})
            if bd:
                score_section += "| Dimension | Score/10 |\n|-----------|----------|\n"
                for dim, sc in bd.items():
                    score_section += f"| {dim} | {sc} |\n"
            score_section += "\n"
        else:
            score_section += "*Strategic score not provided.*\n\n"

        # 11. Confidence Assessment
        conf_section = "## 11. Confidence Assessment\n\n"
        if confidence_calibration:
            conf_section += f"**Confidence Score:** {confidence_calibration.get('score_100', 'N/A')}/100\n\n"
            conf_section += f"**Reasoning:** {confidence_calibration.get('reasoning', '—')}\n\n"
            factors = confidence_calibration.get("supporting_factors", [])
            if factors:
                conf_section += "**Supporting Factors:**\n"
                for f in factors:
                    conf_section += f"- {f}\n"
                conf_section += "\n"
            factors = confidence_calibration.get("reducing_factors", [])
            if factors:
                conf_section += "**Reducing Factors:**\n"
                for f in factors:
                    conf_section += f"- {f}\n"
                conf_section += "\n"
        else:
            conf_section += "*Confidence assessment not provided.*\n\n"

        # Compile full report
        report = f"""# 📊 Research Report: {query}

## 1. Executive Summary

{exec_summary}

---

## 2. Key Findings

{metrics_table if metrics_table else "*No quantitative metrics were extracted.*"}

### Trends & Patterns
{trends_section if trends_section else "*No specific trends identified.*"}

---

## 3. Strategic Reasoning

{reasoning_section.replace('## 🧠 Strategic Reasoning', '').strip()}

---

## 4. Strategic Drivers

{drivers_section.replace('## 🌍 Strategic Drivers', '').strip()}

---

## 5. Competitive Analysis

{detailed_analysis}

---

## 6. Contrarian Intelligence

{contrarian_section.replace('## ⚖️ Contrarian Intelligence', '').strip()}

---

## 7. Scenario Analysis

{scenario_section.replace('### Price Forecast Scenarios', '### Price Forecasts').strip() if scenario_section else '*Scenario analysis not available.*'}

---

{risk_section}

---

{thesis_section}

---

## 10. Strategic Score

{score_section.replace('## 🏆 Strategic Intelligence Score', '').strip()}

---

## 11. Confidence Assessment

{conf_section}

---

{exec_rec_section}

---

## 13. SWOT Analysis

{swot_section if swot_section else "*SWOT analysis not available.*"}

---

## 14. Sources ({len(sources)} total)

{sources_section if sources_section else "*No sources recorded.*"}

---

## ✅ Research Quality Report
{quality_section}

---

*Report generated by DSMI Agent (Deep Strategic Market Intelligence v2)*
"""
        return report


def publisher_node(state: dict) -> dict:
    """
    LangGraph node function for the Publisher agent.
    Reads: everything
    Writes: final_report, executive_summary, swot_analysis, status
    """
    try:
        print(f"\n📝 Publisher: Generating report...")
        
        publisher = PublisherAgent()
        result = publisher.generate_report(
            query=state["original_query"],
            research_plan=state.get("research_plan", ""),
            research_summary=state.get("research_summary", ""),
            metrics=state.get("metrics", []),
            trends=state.get("trends", []),
            comparisons=state.get("comparisons", []),
            analysis_summary=state.get("analysis_summary", ""),
            sources=state.get("sources", []),
            quality_score=state.get("quality_score", 0.0),
            quality_breakdown=state.get("quality_breakdown", {}),
            warnings=state.get("warnings", []),
            strategic_reasoning=state.get("strategic_reasoning", {}),
            strategic_drivers=state.get("strategic_drivers", []),
            valuation_analysis=state.get("valuation_analysis", {}),
            scenario_forecasts=state.get("scenario_forecasts", {}),
            contrarian_intelligence=state.get("contrarian_intelligence", {}),
            strategic_score=state.get("strategic_score", {}),
            confidence_calibration=state.get("confidence_calibration", {}),
            investment_thesis=state.get("investment_thesis", {}),
            executive_recommendations=state.get("executive_recommendations", {}),
        )
        
        report_len = len(result["final_report"])
        print(f"   ✅ Report generated ({report_len} chars)")
        
        return {
            "final_report": result["final_report"],
            "executive_summary": result["executive_summary"],
            "swot_analysis": result["swot_analysis"],
            "status": "Report complete!",
        }
    except Exception as e:
        print(f"   ❌ Publisher error: {e}")
        # Generate a minimal fallback report
        fallback_report = f"""# Research Report: {state['original_query']}

## Summary
{state.get('research_summary', 'Research summary not available.')}

## Analysis
{state.get('analysis_summary', 'Analysis not available.')}

## Sources
{chr(10).join([f"- [{s.get('title', 'Source')}]({s.get('url', '#')})" for s in state.get('sources', [])])}

---
*Report generation encountered errors. This is a simplified report.*
"""
        return {
            "final_report": fallback_report,
            "executive_summary": state.get("analysis_summary", ""),
            "swot_analysis": {},
            "error_log": [f"Publisher error: {str(e)}"],
            "status": "Report generated (with errors).",
        }
