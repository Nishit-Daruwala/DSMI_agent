"""
Researcher Agent - Performs intelligent web research with LLM-powered analysis.

Migration: Internal LLM calls use LangChain ChatPromptTemplate + chain.
Tool usage (SearchTool, WebScraper) unchanged — they are wrapped separately
in tools/langchain_tools.py for LangSmith tracing.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import json

from langchain_core.prompts import ChatPromptTemplate
from tools.search_tool import SearchTool, SearchResult
from tools.scraper import WebScraper, ScrapedContent
from utils.llm_client import get_llm, call_llm, safe_parse_json, truncate_for_llm
from utils.prompts import DSMI_V2_MASTER_PROMPT
from database.vector_store import VectorStore
import uuid
import re


def _check_source_relevance(query: str, title: str, content_snippet: str, threshold: float = 0.2) -> bool:
    """
    Lightweight keyword-based relevance check. No LLM call needed.
    Returns True if the source is relevant to the query.
    
    Logic: Extract meaningful keywords from the query (2+ chars, non-stopwords),
    then check what fraction of them appear in the source title + snippet.
    """
    stopwords = {
        "the", "is", "in", "at", "of", "and", "or", "to", "a", "an", "for",
        "by", "on", "with", "from", "that", "this", "will", "be", "are", "was",
        "what", "how", "which", "who", "when", "where", "why", "can", "do",
        "does", "has", "have", "had", "not", "but", "its", "it", "as", "than",
        "next", "over", "into", "about", "between", "through", "during", "each",
        "our", "their", "these", "those", "such", "should", "would", "could",
        "may", "might", "shall", "must", "need", "also", "most", "more", "very",
    }
    
    # Extract query keywords
    query_words = set(
        w.lower() for w in re.findall(r'\b[a-zA-Z]{2,}\b', query)
        if w.lower() not in stopwords
    )
    
    if not query_words:
        return True  # Can't filter if no keywords
    
    # Check how many query keywords appear in the source
    source_text = f"{title} {content_snippet}".lower()
    matches = sum(1 for kw in query_words if kw in source_text)
    relevance_score = matches / len(query_words)
    
    return relevance_score >= threshold


@dataclass
class ResearchResult:
    """Represents the result of a research query"""
    query: str
    summary: str
    sources: List[Dict[str, str]]  # [{title, url, snippet}]
    key_findings: List[str]
    data_points: Dict[str, Any]  # Extracted numbers, stats, etc.
    is_complete: bool = False
    needs_more_research: List[str] = field(default_factory=list)


class ResearcherAgent:
    """
    AI-powered research agent that searches the web, reads content,
    and synthesizes information using an LLM.
    """
    
    def __init__(self, model: str = "gemini-2.0-flash"):
        self.search_tool = SearchTool()
        self.scraper = WebScraper()
        self.model = model
        self.vector_store = VectorStore()
    
    def research(self, query: str, depth: int = 2, max_sources: int = 5) -> ResearchResult:
        """
        Perform comprehensive research on a query.
        
        Args:
            query: The research question
            depth: How many levels of follow-up searches to perform (1-3)
            max_sources: Maximum number of sources to analyze
            
        Returns:
            ResearchResult with synthesized findings
        """
        print(f"\n🔍 Researching: {query}")
        
        # Step 1: Initial search
        search_results = self.search_tool.search(query, max_results=max_sources)
        print(f"   Found {len(search_results)} initial results")
        
        # Step 2: Scrape top sources for full content
        sources = []
        full_content = []
        
        for result in search_results[:max_sources]:
            print(f"   📄 Reading: {result.title[:50]}...")
            scraped = self.scraper.scrape_url(result.url)
            
            if scraped.success and scraped.text:
                # Relevance filter: skip sources that don't match the query
                if not _check_source_relevance(query, result.title, result.content[:300]):
                    print(f"      ⏭️ Skipped irrelevant source: {result.title[:50]}")
                    continue
                sources.append({
                    "title": result.title,
                    "url": result.url,
                    "snippet": result.content[:300]
                })
                full_content.append({
                    "title": result.title,
                    "url": result.url,
                    "content": scraped.text[:5000]  # Richer content extraction for deeper analysis
                })
        
        # Step 3: LLM Analysis - Synthesize findings
        print("   🧠 Analyzing content...")
        analysis = self._analyze_content(query, full_content)
        
        # Step 4: Assess completeness and identify gaps
        completeness = self._assess_completeness(query, analysis)
        
        # Step 5: Follow-up research if needed and depth allows
        if depth > 1 and completeness.get("gaps"):
            print(f"   🔄 Following up on {len(completeness['gaps'])} gaps...")
            for gap in completeness["gaps"][:2]:  # Max 2 follow-ups
                follow_up_results = self.search_tool.search(gap, max_results=2)
                for result in follow_up_results:
                    scraped = self.scraper.scrape_url(result.url)
                    if scraped.success:
                        # Relevance filter for follow-up sources too
                        if not _check_source_relevance(query, result.title, result.content[:300]):
                            print(f"      ⏭️ Skipped irrelevant follow-up: {result.title[:50]}")
                            continue
                        sources.append({
                            "title": result.title,
                            "url": result.url,
                            "snippet": result.content[:300]
                        })
                        full_content.append({
                            "title": result.title,
                            "url": result.url,
                            "content": scraped.text[:3500]
                        })
            
            # Re-analyze with new content
            analysis = self._analyze_content(query, full_content)
            completeness = self._assess_completeness(query, analysis)
        
        # Store in Vector DB if we got a substantial summary
        summary = analysis.get("summary", "")
        if len(summary) > 50:
            try:
                # We use a placeholder session ID for ad-hoc research, or a real one if passed
                session_id = str(uuid.uuid4())
                self.vector_store.store_research(
                    session_id=session_id,
                    content=f"Query: {query}\n\nSummary:\n{summary}\n\nFacts:\n{analysis.get('key_findings', [])}",
                    metadata={"query": query, "source_count": len(sources)}
                )
            except Exception as e:
                print(f"   [Researcher] Failed to store research in Vector DB: {e}")
        
        return ResearchResult(
            query=query,
            summary=summary,
            sources=sources,
            key_findings=analysis.get("key_findings", []),
            data_points=analysis.get("data_points", {}),
            is_complete=completeness.get("is_complete", False),
            needs_more_research=completeness.get("gaps", [])
        )
    
    def _analyze_content(self, query: str, content: List[Dict]) -> Dict[str, Any]:
        """Use LLM (via LangChain chain) to analyze and synthesize content."""
        
        content_text = "\n\n".join([
            f"Source: {c['title']}\nURL: {c['url']}\nContent: {c['content']}"
            for c in content
        ])
        
        content_text = truncate_for_llm(content_text, max_chars=12000)
        
        system_msg = DSMI_V2_MASTER_PROMPT + """

You are a Research Analyst. Analyze content and extract key information. Always respond with valid JSON.
RULE #3 & #4: Validate evidence and respect the Evidence Hierarchy (Tier 1 > Tier 5). If sources conflict, highlight the contradiction and lean towards the higher-tier source."""
        # LangChain prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_msg),
            ("human", """Analyze the following content to answer this research question:
"{query}"

Content from sources:
{content_text}

Provide a JSON response with:
1. "summary": A comprehensive 2-3 paragraph summary answering the question
2. "key_findings": A list of 5-7 key findings/facts (strings)
3. "data_points": An object with any specific numbers, statistics, dates mentioned (e.g., {{"market_size": "$5B", "growth_rate": "15%", "year": "2024"}})
4. "confidence": A score from 1-10 on how well the sources answer the question

Respond ONLY with valid JSON.""")
        ])
        
        try:
            llm = get_llm(model=self.model, temperature=0.3)
            llm = llm.bind(response_mime_type="application/json")
            chain = prompt | llm
            response = chain.invoke({"query": query, "content_text": content_text})
            return safe_parse_json(
                response.content,
                fallback={
                    "summary": "Analysis failed",
                    "key_findings": [],
                    "data_points": {},
                    "confidence": 0
                }
            )
        except Exception as e:
            print(f"   ⚠️ Analysis chain error: {e}")
            return {
                "summary": "Analysis failed",
                "key_findings": [],
                "data_points": {},
                "confidence": 0
            }
    
    def _assess_completeness(self, query: str, analysis: Dict) -> Dict[str, Any]:
        """Assess if research is complete or needs more investigation."""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You assess research completeness. Respond with valid JSON only."),
            ("human", """Given this research question and analysis, determine if the research is complete.

Question: "{query}"

Current Analysis Summary: {summary}
Key Findings: {key_findings}
Data Points: {data_points}

Respond with JSON:
1. "is_complete": true/false - Is the research comprehensive enough?
2. "gaps": A list of specific topics that need more research (empty if complete)
3. "reason": Brief explanation""")
        ])
        
        try:
            llm = get_llm(model=self.model, temperature=0.2)
            llm = llm.bind(response_mime_type="application/json")
            chain = prompt | llm
            response = chain.invoke({
                "query": query,
                "summary": analysis.get("summary", "No summary"),
                "key_findings": str(analysis.get("key_findings", [])),
                "data_points": str(analysis.get("data_points", {})),
            })
            return safe_parse_json(
                response.content,
                fallback={"is_complete": True, "gaps": [], "reason": "Assessment failed"}
            )
        except Exception as e:
            print(f"   ⚠️ Completeness chain error: {e}")
            return {"is_complete": True, "gaps": [], "reason": "Assessment failed"}
    
    def summarize_sources(self, sources: List[str]) -> str:
        """Summarize multiple text sources into a coherent narrative."""
        
        combined = "\n\n---\n\n".join(sources)
        combined = truncate_for_llm(combined, max_chars=8000)
        
        system_msg = DSMI_V2_MASTER_PROMPT + """

You are a skilled summarizer. Create clear, informative summaries. Apply Evidence Validation and Hierarchy rules."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_msg),
            ("human", """Summarize the following sources into a coherent narrative:

{combined}

Provide a clear, well-structured summary that captures the key information.""")
        ])
        
        try:
            llm = get_llm(model=self.model, temperature=0.3)
            chain = prompt | llm
            response = chain.invoke({"combined": combined})
            return response.content
        except Exception as e:
            return f"Summarization failed: {e}"
    
    def quick_answer(self, question: str) -> str:
        """Get a quick answer using Tavily's QnA feature + LLM enhancement."""
        
        # Try direct answer first
        direct_answer = self.search_tool.get_answer(question)
        
        if direct_answer:
            return direct_answer
        
        # Fall back to search + synthesize
        results = self.search_tool.search(question, max_results=3)
        content = "\n".join([r.content for r in results])
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "Answer questions accurately and concisely."),
            ("human", """Answer this question based on the search results:
Question: {question}

Search Results:
{content}

Provide a concise, accurate answer.""")
        ])
        
        try:
            llm = get_llm(model=self.model, temperature=0.2)
            chain = prompt | llm
            response = chain.invoke({"question": question, "content": content})
            return response.content
        except Exception as e:
            return f"Could not answer: {e}"


def researcher_node(state: dict) -> dict:
    """
    LangGraph node function for the Researcher agent.
    Reads: sub_tasks, original_query
    Writes: raw_content, sources, research_summary, status
    """
    try:
        sub_tasks = state.get("sub_tasks", [])
        query = state["original_query"]
        
        # If no sub-tasks, use original query
        if not sub_tasks:
            sub_tasks = [{"id": 1, "query": query, "priority": 1}]
        
        print(f"\n🔍 Researcher: Processing {len(sub_tasks)} sub-tasks...")
        
        agent = ResearcherAgent()
        all_content = list(state.get("raw_content", []))
        all_sources = list(state.get("sources", []))
        summaries = []
        
        # Track existing URLs to avoid duplicates
        existing_urls = {s.get("url") for s in all_sources}
        
        for task in sub_tasks:
            task_query = task.get("query", query)
            priority = task.get("priority", 1)
            
            # Adjust depth based on priority
            depth = 2 if priority <= 2 else 1
            max_sources = 4 if priority <= 2 else 2
            
            print(f"   🔎 [{priority}] {task_query[:60]}...")
            
            try:
                result = agent.research(
                    query=task_query,
                    depth=depth,
                    max_sources=max_sources
                )
                
                # Aggregate content (avoid duplicates)
                for source in result.sources:
                    if source.get("url") not in existing_urls:
                        all_sources.append(source)
                        existing_urls.add(source.get("url"))
                        all_content.append({
                            "title": source.get("title", ""),
                            "url": source.get("url", ""),
                            "content": source.get("snippet", ""),
                            "source_query": task_query,
                        })
                
                if result.summary:
                    summaries.append(f"**{task_query}**: {result.summary}")
                    
            except Exception as e:
                print(f"      ⚠️ Sub-task failed: {e}")
                # error_log uses Annotated reducer — return only new errors
                return {
                    "raw_content": all_content,
                    "sources": all_sources,
                    "research_summary": "\n\n".join(summaries) if summaries else "Partial research results.",
                    "error_log": [f"Research sub-task failed: {task_query}: {str(e)}"],
                    "status": f"Research partially complete with errors.",
                }
        
        # Combine summaries
        combined_summary = "\n\n".join(summaries) if summaries else "No research results obtained."
        
        print(f"   ✅ Research complete: {len(all_sources)} sources gathered")
        
        return {
            "raw_content": all_content,
            "sources": all_sources,
            "research_summary": combined_summary,
            "status": f"Research complete. {len(all_sources)} sources from {len(sub_tasks)} sub-tasks.",
        }
    except Exception as e:
        print(f"   ❌ Researcher error: {e}")
        return {
            "raw_content": list(state.get("raw_content", [])),
            "sources": list(state.get("sources", [])),
            "research_summary": "Research failed due to an error.",
            "error_log": [f"Researcher error: {str(e)}"],
            "status": "Research failed.",
        }


if __name__ == "__main__":
    # Test the researcher agent
    print("=== Testing Researcher Agent ===\n")
    
    agent = ResearcherAgent()
    
    # Test research
    result = agent.research(
        "What is the current market size and growth rate of green hydrogen in India?",
        depth=2,
        max_sources=3
    )
    
    print("\n" + "="*50)
    print("RESEARCH RESULTS")
    print("="*50)
    print(f"\nQuery: {result.query}")
    print(f"\nSummary:\n{result.summary}")
    print(f"\nKey Findings:")
    for i, finding in enumerate(result.key_findings, 1):
        print(f"  {i}. {finding}")
    print(f"\nData Points: {result.data_points}")
    print(f"\nSources Used: {len(result.sources)}")
    print(f"Research Complete: {result.is_complete}")
    if result.needs_more_research:
        print(f"Gaps: {result.needs_more_research}")
