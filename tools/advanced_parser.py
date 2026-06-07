import os
from typing import List, Dict, Any, Optional
from unstructured.partition.auto import partition
from unstructured.cleaners.core import clean_extra_whitespace

class AdvancedDocumentParser:
    """
    Handles extracting text and tables from complex documents like PDFs, DOCX, and HTML.
    Utilizes Unstructured.io for robust layout detection and parsing.
    """
    
    def __init__(self):
        pass
        
    def parse_document(self, file_path: str, strategy: str = "fast") -> str:
        """
        Auto-detects format and parses the document into plain text.
        
        Args:
            file_path: Path to the local file to parse
            strategy: "fast" (text-only, quick) or "hi_res" (OCR + Layout, slow but accurate)
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        print(f"Parsing document: {file_path} (Strategy: {strategy})")
        
        # Unstructured automatically detects file type
        elements = partition(
            filename=file_path,
            strategy=strategy,
            # If hi_res is used, wait for OCR to process tables and images
            pdf_infer_table_structure=(strategy == "hi_res")
        )
        
        # Join the text content of all extracted elements
        full_text = "\n\n".join([str(el) for el in elements])
        
        # Clean up whitespace
        cleaned_text = clean_extra_whitespace(full_text)
        
        return cleaned_text

    def extract_tables(self, file_path: str) -> List[str]:
        """
        Specifically extracts tabular data from a document as a list of HTML/Markdown tables.
        Requires strategy="hi_res" to accurately map table boundaries in PDFs.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        print(f"Extracting tables from: {file_path}")
        
        elements = partition(
            filename=file_path,
            strategy="hi_res",
            pdf_infer_table_structure=True
        )
        
        tables = []
        for el in elements:
            if el.category == "Table":
                # Unstructured usually provides HTML representation of tables in the metadata
                if hasattr(el, 'metadata') and hasattr(el.metadata, 'text_as_html'):
                    tables.append(str(el.metadata.text_as_html))
                else:
                    tables.append(str(el))
                    
        return tables

    def parse_10k_filing(self, file_path: str) -> Dict[str, Any]:
        """
        Specialized parser for SEC 10-K filings.
        Extracts key sections like Business Overview, Risk Factors, Financial Statements.
        Falls back to general parsing if section headers are not found.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        print(f"Parsing 10-K filing: {file_path}")

        full_text = self.parse_document(file_path, strategy="hi_res")
        tables = self.extract_tables(file_path)

        # Try to extract common 10-K sections by header keywords
        sections = {
            "business_overview": "",
            "risk_factors": "",
            "financial_statements": "",
            "management_discussion": "",
        }

        section_keywords = {
            "business_overview": ["item 1", "business overview", "description of business"],
            "risk_factors": ["item 1a", "risk factors"],
            "financial_statements": ["item 8", "financial statements", "consolidated balance"],
            "management_discussion": ["item 7", "management's discussion", "md&a"],
        }

        text_lower = full_text.lower()
        for section_key, keywords in section_keywords.items():
            for kw in keywords:
                idx = text_lower.find(kw)
                if idx != -1:
                    # Grab up to 5000 chars from the start of that section
                    sections[section_key] = full_text[idx : idx + 5000]
                    break

        return {
            "full_text": full_text,
            "sections": sections,
            "tables": tables,
        }

    def chunk_document(self, text: str, chunk_size: int = 4000, overlap: int = 500) -> List[str]:
        """
        Splits large documents into overlapping chunks for LLM processing or vector DB storage.
        """
        if not text:
            return []
            
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = min(start + chunk_size, text_length)
            
            # Try to snap the chunk end to a paragraph or sentence boundary
            if end < text_length:
                # Look for a paragraph break
                last_para = text.rfind('\n\n', start, end)
                if last_para != -1 and last_para > start + (chunk_size // 2):
                    end = last_para + 2
                else:
                    # Look for a sentence break
                    last_sent = max(text.rfind('. ', start, end), text.rfind('! ', start, end), text.rfind('? ', start, end))
                    if last_sent != -1 and last_sent > start + (chunk_size // 2):
                        end = last_sent + 2
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
                
            start = end - overlap
            
        return chunks
