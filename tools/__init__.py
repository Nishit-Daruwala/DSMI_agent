"""
Tools package - Search, scraping, and document reading utilities

Includes both raw tool classes and LangChain @tool wrappers.
- Raw classes: Use directly in agent code (SearchTool, WebScraper, PDFReader)
- LangChain tools: For LangSmith tracing and agent binding (web_search, scrape_webpage, etc.)
"""
from tools.search_tool import SearchTool, SearchResult, quick_search
from tools.scraper import WebScraper, ScrapedContent, scrape
from tools.pdf_reader import PDFReader, PDFContent, read_pdf
from tools.langchain_tools import web_search, search_news, scrape_webpage, read_pdf_from_url, ALL_TOOLS

__all__ = [
    # Raw tool classes
    "SearchTool", "SearchResult", "quick_search",
    "WebScraper", "ScrapedContent", "scrape", 
    "PDFReader", "PDFContent", "read_pdf",
    # LangChain tool wrappers
    "web_search", "search_news", "scrape_webpage", "read_pdf_from_url",
    "ALL_TOOLS",
]
