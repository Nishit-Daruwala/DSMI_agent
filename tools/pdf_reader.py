"""
PDF Reader Tool - Extract text and tables from PDF documents
"""
import os
import requests
import tempfile
from dataclasses import dataclass
from typing import List, Optional
import pandas as pd

# Try multiple PDF libraries for robustness
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False


@dataclass
class PDFContent:
    """Represents extracted PDF content"""
    filename: str
    text: str
    pages: int
    tables: List[pd.DataFrame]
    success: bool = True
    error: str = ""


class PDFReader:
    """
    PDF reader for extracting text and tables from PDF documents.
    Supports both local files and URLs.
    """
    
    def __init__(self):
        if not PYMUPDF_AVAILABLE and not PDFPLUMBER_AVAILABLE:
            raise ImportError("Please install pymupdf or pdfplumber: pip install pymupdf pdfplumber")
    
    def read_pdf(self, path: str) -> PDFContent:
        """
        Read and extract content from a PDF file.
        
        Args:
            path: Path to the PDF file
            
        Returns:
            PDFContent object with extracted text and tables
        """
        if not os.path.exists(path):
            return PDFContent(
                filename=path,
                text="",
                pages=0,
                tables=[],
                success=False,
                error=f"File not found: {path}"
            )
        
        try:
            if PYMUPDF_AVAILABLE:
                return self._read_with_pymupdf(path)
            else:
                return self._read_with_pdfplumber(path)
                
        except Exception as e:
            return PDFContent(
                filename=path,
                text="",
                pages=0,
                tables=[],
                success=False,
                error=str(e)
            )
    
    def read_pdf_from_url(self, url: str) -> PDFContent:
        """
        Download and read a PDF from a URL.
        
        Args:
            url: URL of the PDF file
            
        Returns:
            PDFContent object with extracted text and tables
        """
        try:
            # Download PDF to temp file
            response = requests.get(url, timeout=30, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            response.raise_for_status()
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
                tmp_file.write(response.content)
                tmp_path = tmp_file.name
            
            # Read the PDF
            result = self.read_pdf(tmp_path)
            result.filename = url
            
            # Clean up temp file
            os.unlink(tmp_path)
            
            return result
            
        except requests.RequestException as e:
            return PDFContent(
                filename=url,
                text="",
                pages=0,
                tables=[],
                success=False,
                error=f"Download failed: {str(e)}"
            )
    
    def _read_with_pymupdf(self, path: str) -> PDFContent:
        """Read PDF using PyMuPDF (fitz)"""
        doc = fitz.open(path)
        
        text_parts = []
        tables = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Extract text
            text_parts.append(f"--- Page {page_num + 1} ---\n")
            text_parts.append(page.get_text())
            
            # Try to extract tables
            try:
                page_tables = page.find_tables()
                for table in page_tables:
                    df = pd.DataFrame(table.extract())
                    if not df.empty:
                        # Use first row as header if it looks like a header
                        if len(df) > 1:
                            df.columns = df.iloc[0]
                            df = df[1:]
                        tables.append(df)
            except Exception:
                pass
        
        doc.close()
        
        return PDFContent(
            filename=os.path.basename(path),
            text="\n".join(text_parts),
            pages=len(doc),
            tables=tables,
            success=True
        )
    
    def _read_with_pdfplumber(self, path: str) -> PDFContent:
        """Read PDF using pdfplumber"""
        text_parts = []
        tables = []
        
        with pdfplumber.open(path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                # Extract text
                text_parts.append(f"--- Page {page_num + 1} ---\n")
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
                
                # Extract tables
                page_tables = page.extract_tables()
                for table in page_tables:
                    if table:
                        df = pd.DataFrame(table[1:], columns=table[0])
                        if not df.empty:
                            tables.append(df)
            
            num_pages = len(pdf.pages)
        
        return PDFContent(
            filename=os.path.basename(path),
            text="\n".join(text_parts),
            pages=num_pages,
            tables=tables,
            success=True
        )
    
    def extract_text_only(self, path: str) -> str:
        """
        Extract only text from a PDF (faster, no table extraction).
        
        Args:
            path: Path to PDF file
            
        Returns:
            Extracted text as string
        """
        result = self.read_pdf(path)
        return result.text if result.success else ""
    
    def get_page_count(self, path: str) -> int:
        """Get the number of pages in a PDF."""
        if PYMUPDF_AVAILABLE:
            doc = fitz.open(path)
            count = len(doc)
            doc.close()
            return count
        elif PDFPLUMBER_AVAILABLE:
            with pdfplumber.open(path) as pdf:
                return len(pdf.pages)
        return 0


# Convenience function
def read_pdf(path: str) -> PDFContent:
    """Quick PDF read utility function"""
    reader = PDFReader()
    return reader.read_pdf(path)


if __name__ == "__main__":
    # Test the PDF reader
    print("=== Testing PDF Reader ===\n")
    
    reader = PDFReader()
    
    # Test with a sample PDF URL
    print("Testing with online PDF...")
    result = reader.read_pdf_from_url("https://www.w3.org/WAI/WCAG21/Techniques/pdf/img/table-word.pdf")
    
    if result.success:
        print(f"Filename: {result.filename}")
        print(f"Pages: {result.pages}")
        print(f"Tables Found: {len(result.tables)}")
        print(f"Text Length: {len(result.text)} characters")
        print(f"\nFirst 500 chars:\n{result.text[:500]}...")
    else:
        print(f"Error: {result.error}")
