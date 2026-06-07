"""
Search Tool - Tavily API wrapper for intelligent web search
"""
from tavily import TavilyClient
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import List, Optional
import os

load_dotenv()


@dataclass
class SearchResult:
    """Represents a single search result"""
    title: str
    url: str
    content: str
    score: float = 0.0
    

class SearchTool:
    """
    Intelligent search tool using Tavily API.
    Provides web search, news search, and direct answer extraction.
    """
    
    def __init__(self):
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise ValueError("TAVILY_API_KEY not found in environment variables")
        self.client = TavilyClient(api_key=api_key)
    
    def search(self, query: str, max_results: int = 10, search_depth: str = "advanced") -> List[SearchResult]:
        """
        Perform a comprehensive web search.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return (default: 10)
            search_depth: "basic" for fast, "advanced" for thorough (default: advanced)
            
        Returns:
            List of SearchResult objects
        """
        try:
            response = self.client.search(
                query=query,
                max_results=max_results,
                search_depth=search_depth,
                include_answer=True
            )
            
            results = []
            for item in response.get("results", []):
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    content=item.get("content", ""),
                    score=item.get("score", 0.0)
                ))
            
            return results
            
        except Exception as e:
            print(f"Search error: {e}")
            return []
    
    def search_news(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """
        Search for recent news articles.
        
        Args:
            query: News search query
            max_results: Maximum number of news results
            
        Returns:
            List of SearchResult objects from news sources
        """
        try:
            response = self.client.search(
                query=query,
                max_results=max_results,
                search_depth="basic",
                topic="news"
            )
            
            results = []
            for item in response.get("results", []):
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    content=item.get("content", ""),
                    score=item.get("score", 0.0)
                ))
            
            return results
            
        except Exception as e:
            print(f"News search error: {e}")
            return []
    
    def get_answer(self, query: str) -> Optional[str]:
        """
        Get a direct answer to a question using Tavily's QnA feature.
        
        Args:
            query: Question to answer
            
        Returns:
            Direct answer string or None if not available
        """
        try:
            response = self.client.qna_search(query=query)
            return response if response else None
            
        except Exception as e:
            print(f"Answer extraction error: {e}")
            return None
    
    def search_with_context(self, query: str, context: str = "", max_results: int = 5) -> List[SearchResult]:
        """
        Search with additional context for more relevant results.
        
        Args:
            query: Main search query
            context: Additional context to refine search
            max_results: Maximum results to return
            
        Returns:
            List of contextually relevant SearchResult objects
        """
        enhanced_query = f"{context} {query}" if context else query
        return self.search(enhanced_query, max_results=max_results)


# Convenience function for quick searches
def quick_search(query: str, max_results: int = 5) -> List[SearchResult]:
    """Quick search utility function"""
    tool = SearchTool()
    return tool.search(query, max_results=max_results)


if __name__ == "__main__":
    # Test the search tool
    tool = SearchTool()
    
    print("=== Testing Search Tool ===\n")
    
    # Test basic search
    results = tool.search("AI startups in India 2024", max_results=3)
    print(f"Found {len(results)} results:")
    for r in results:
        print(f"  - {r.title}")
        print(f"    URL: {r.url}")
        print(f"    Score: {r.score}\n")
    
    # Test direct answer
    answer = tool.get_answer("What is the market size of green hydrogen in India?")
    print(f"\nDirect Answer: {answer}")
