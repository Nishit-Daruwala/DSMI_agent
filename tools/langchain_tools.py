"""
LangChain Tool Wrappers - Wraps existing tool classes as LangChain @tool functions.

These wrappers make the existing SearchTool, WebScraper, and PDFReader classes
compatible with LangChain's tool ecosystem, enabling:
- Automatic tracing in LangSmith
- Compatible with LangGraph ToolNode (if needed in future)
- Structured tool descriptions for agent binding
"""
from langchain_core.tools import tool
from tools.search_tool import SearchTool
from tools.scraper import WebScraper
from tools.pdf_reader import PDFReader


@tool
def web_search(query: str, max_results: int = 5) -> str:
    """Search the web for real-time market data, competitor info, financial metrics, and industry reports.
    
    Args:
        query: The search query string
        max_results: Maximum number of results to return (default: 5)
    
    Returns:
        Formatted search results with title, URL, and content snippet for each result.
    """
    search_tool = SearchTool()
    results = search_tool.search(query, max_results=max_results)
    
    if not results:
        return "No search results found."
    
    formatted = []
    for r in results:
        formatted.append(
            f"Title: {r.title}\n"
            f"URL: {r.url}\n"
            f"Content: {r.content}\n"
            f"Score: {r.score}\n"
            f"---"
        )
    return "\n".join(formatted)


@tool
def search_news(query: str, max_results: int = 5) -> str:
    """Search for recent news articles about a topic.
    
    Args:
        query: News search query
        max_results: Maximum number of news results (default: 5)
    
    Returns:
        Formatted news results with title, URL, and content snippet.
    """
    search_tool = SearchTool()
    results = search_tool.search_news(query, max_results=max_results)
    
    if not results:
        return "No news results found."
    
    formatted = []
    for r in results:
        formatted.append(
            f"Title: {r.title}\n"
            f"URL: {r.url}\n"
            f"Content: {r.content}\n"
            f"---"
        )
    return "\n".join(formatted)


@tool
def scrape_webpage(url: str) -> str:
    """Scrape and extract text content from a webpage URL.
    
    Args:
        url: The URL of the webpage to scrape
    
    Returns:
        Extracted text content from the webpage, or error message if scraping fails.
    """
    scraper = WebScraper()
    result = scraper.scrape_url(url)
    
    if not result.success:
        return f"Failed to scrape {url}: {result.error}"
    
    # Return truncated content to avoid overwhelming the LLM
    text = result.text[:5000]
    return (
        f"Title: {result.title}\n"
        f"URL: {url}\n"
        f"Content ({len(result.text)} chars total, showing first 5000):\n"
        f"{text}"
    )


@tool
def read_pdf_from_url(url: str) -> str:
    """Download and extract text from a PDF document at the given URL.
    
    Args:
        url: The URL of the PDF file to read
    
    Returns:
        Extracted text content from the PDF, or error message if reading fails.
    """
    reader = PDFReader()
    result = reader.read_pdf_from_url(url)
    
    if not result.success:
        return f"Failed to read PDF from {url}: {result.error}"
    
    # Return truncated content
    text = result.text[:5000]
    return (
        f"PDF: {result.filename}\n"
        f"Pages: {result.pages}\n"
        f"Tables Found: {len(result.tables)}\n"
        f"Content ({len(result.text)} chars total, showing first 5000):\n"
        f"{text}"
    )


# Export all tools as a list for easy binding
ALL_TOOLS = [web_search, search_news, scrape_webpage, read_pdf_from_url]
