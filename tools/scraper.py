"""
Web Scraper Tool - Extract content from web pages
"""
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import re
from urllib.parse import urljoin, urlparse
import pandas as pd
import io


@dataclass
class ScrapedContent:
    """Represents scraped content from a webpage"""
    url: str
    title: str
    text: str
    links: List[str]
    tables: List[pd.DataFrame]
    meta_description: str = ""
    success: bool = True
    error: str = ""


class WebScraper:
    """
    Web scraper for extracting content from websites.
    Handles text extraction, table parsing, and link discovery.
    """
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
    
    def scrape_url(self, url: str) -> ScrapedContent:
        """
        Scrape content from a URL.
        
        Args:
            url: The URL to scrape
            
        Returns:
            ScrapedContent object with extracted data
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract title
            title = ""
            if soup.title:
                title = soup.title.string or ""
            
            # Extract meta description
            meta_desc = ""
            meta_tag = soup.find("meta", attrs={"name": "description"})
            if meta_tag:
                meta_desc = meta_tag.get("content", "")
            
            # Extract main text
            text = self.extract_text(soup)
            
            # Extract links
            links = self.extract_links(soup, url)
            
            # Extract tables
            tables = self.extract_tables(soup)
            
            return ScrapedContent(
                url=url,
                title=title.strip(),
                text=text,
                links=links,
                tables=tables,
                meta_description=meta_desc,
                success=True
            )
            
        except requests.RequestException as e:
            return ScrapedContent(
                url=url,
                title="",
                text="",
                links=[],
                tables=[],
                success=False,
                error=str(e)
            )
    
    def extract_text(self, soup: BeautifulSoup) -> str:
        """
        Extract clean text from HTML.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            Cleaned text content
        """
        # Remove unwanted elements
        for element in soup(["script", "style", "nav", "footer", "header", "aside", "form", "noscript"]):
            element.decompose()
        
        # Get text from main content areas
        main_content = soup.find("main") or soup.find("article") or soup.find("div", class_=re.compile(r"content|article|post|entry"))
        
        if main_content:
            text = main_content.get_text(separator="\n", strip=True)
        else:
            text = soup.get_text(separator="\n", strip=True)
        
        # Clean up whitespace
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        text = "\n".join(lines)
        
        # Remove excessive newlines
        text = re.sub(r"\n{3,}", "\n\n", text)
        
        return text
    
    def extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """
        Extract all links from the page.
        
        Args:
            soup: BeautifulSoup object
            base_url: Base URL for resolving relative links
            
        Returns:
            List of absolute URLs
        """
        links = []
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            # Convert relative URLs to absolute
            absolute_url = urljoin(base_url, href)
            # Only include http/https links
            if absolute_url.startswith(("http://", "https://")):
                links.append(absolute_url)
        
        return list(set(links))  # Remove duplicates
    
    def extract_tables(self, soup: BeautifulSoup) -> List[pd.DataFrame]:
        """
        Extract tables from HTML as DataFrames.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            List of pandas DataFrames
        """
        tables = []
        for table in soup.find_all("table"):
            try:
                # Convert HTML table to DataFrame
                df = pd.read_html(io.StringIO(str(table)))[0]
                if not df.empty and len(df) > 1:  # Skip trivial tables
                    tables.append(df)
            except Exception:
                continue
        
        return tables
    
    def scrape_multiple(self, urls: List[str]) -> List[ScrapedContent]:
        """
        Scrape multiple URLs.
        
        Args:
            urls: List of URLs to scrape
            
        Returns:
            List of ScrapedContent objects
        """
        return [self.scrape_url(url) for url in urls]
    
    def get_page_summary(self, url: str, max_length: int = 1000) -> str:
        """
        Get a brief summary of a page's content.
        
        Args:
            url: URL to summarize
            max_length: Maximum character length of summary
            
        Returns:
            Truncated text content
        """
        content = self.scrape_url(url)
        if content.success:
            text = content.text[:max_length]
            if len(content.text) > max_length:
                text += "..."
            return text
        return f"Failed to scrape: {content.error}"


# Convenience function
def scrape(url: str) -> ScrapedContent:
    """Quick scrape utility function"""
    scraper = WebScraper()
    return scraper.scrape_url(url)


if __name__ == "__main__":
    # Test the scraper
    scraper = WebScraper()
    
    print("=== Testing Web Scraper ===\n")
    
    result = scraper.scrape_url("https://en.wikipedia.org/wiki/Artificial_intelligence")
    
    if result.success:
        print(f"Title: {result.title}")
        print(f"Meta Description: {result.meta_description[:100]}...")
        print(f"Text Length: {len(result.text)} characters")
        print(f"Links Found: {len(result.links)}")
        print(f"Tables Found: {len(result.tables)}")
        print(f"\nFirst 500 chars of content:\n{result.text[:500]}...")
    else:
        print(f"Error: {result.error}")
