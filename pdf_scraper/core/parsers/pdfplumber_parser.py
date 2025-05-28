import pdfplumber
from typing import Dict, List, Any
from .base import BaseParser

class PDFPlumberParser(BaseParser):
    """PDF parser implementation using pdfplumber."""
    
    def __init__(self, file_path: str):
        super().__init__(file_path)
        self.pdf = pdfplumber.open(file_path)
    
    def extract_text(self) -> str:
        """Extract all text from the PDF using pdfplumber."""
        text = ""
        for page in self.pdf.pages:
            text += page.extract_text() or ""
        return text
    
    def extract_tables(self) -> List[Dict[str, Any]]:
        """Extract tables from the PDF using pdfplumber."""
        tables = []
        for i, page in enumerate(self.pdf.pages, 1):
            page_tables = page.extract_tables()
            if page_tables:
                for table in page_tables:
                    tables.append({
                        "page": i,
                        "table": table
                    })
        return tables
    
    def extract_metadata(self) -> Dict[str, Any]:
        """Extract PDF metadata using pdfplumber."""
        metadata = {}
        if self.pdf.metadata:
            metadata = {
                "title": self.pdf.metadata.get("Title"),
                "author": self.pdf.metadata.get("Author"),
                "subject": self.pdf.metadata.get("Subject"),
                "keywords": self.pdf.metadata.get("Keywords"),
                "creator": self.pdf.metadata.get("Creator"),
                "producer": self.pdf.metadata.get("Producer"),
                "creation_date": self.pdf.metadata.get("CreationDate"),
                "modification_date": self.pdf.metadata.get("ModDate")
            }
        return metadata
    
    def extract_images(self) -> List[Dict[str, Any]]:
        """Extract images from the PDF using pdfplumber."""
        images = []
        for i, page in enumerate(self.pdf.pages, 1):
            if page.images:
                for img in page.images:
                    images.append({
                        "page": i,
                        "x0": img["x0"],
                        "y0": img["y0"],
                        "x1": img["x1"],
                        "y1": img["y1"],
                        "width": img["width"],
                        "height": img["height"],
                        "type": img["name"]
                    })
        return images
    
    def get_page_count(self) -> int:
        """Get total number of pages in the PDF."""
        return len(self.pdf.pages)
    
    def extract_page(self, page_number: int) -> Dict[str, Any]:
        """Extract content from a specific page."""
        if not 1 <= page_number <= len(self.pdf.pages):
            raise ValueError(f"Page number {page_number} out of range")
        
        page = self.pdf.pages[page_number - 1]
        return {
            "text": page.extract_text(),
            "tables": page.extract_tables(),
            "images": [img for img in page.images],
            "width": page.width,
            "height": page.height
        }
    
    def __del__(self):
        """Close the PDF file when the parser is destroyed."""
        if hasattr(self, 'pdf'):
            self.pdf.close() 