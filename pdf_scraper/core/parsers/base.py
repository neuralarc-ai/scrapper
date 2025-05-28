from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import os

class BaseParser(ABC):
    """Base class for PDF parsers."""
    
    def __init__(self, file_path: str):
        """Initialize parser with PDF file path.
        
        Args:
            file_path: Path to the PDF file
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found: {file_path}")
        self.file_path = file_path
        
    @abstractmethod
    def extract_text(self) -> str:
        """Extract all text from the PDF.
        
        Returns:
            str: Extracted text content
        """
        pass
    
    @abstractmethod
    def extract_tables(self) -> List[Dict[str, Any]]:
        """Extract tables from the PDF.
        
        Returns:
            List[Dict[str, Any]]: List of extracted tables with metadata
        """
        pass
    
    @abstractmethod
    def extract_metadata(self) -> Dict[str, Any]:
        """Extract PDF metadata.
        
        Returns:
            Dict[str, Any]: PDF metadata including author, title, etc.
        """
        pass
    
    @abstractmethod
    def extract_images(self) -> List[Dict[str, Any]]:
        """Extract images from the PDF.
        
        Returns:
            List[Dict[str, Any]]: List of extracted images with metadata
        """
        pass
    
    @abstractmethod
    def get_page_count(self) -> int:
        """Get total number of pages in the PDF.
        
        Returns:
            int: Number of pages
        """
        pass
    
    @abstractmethod
    def extract_page(self, page_number: int) -> Dict[str, Any]:
        """Extract content from a specific page.
        
        Args:
            page_number: Page number to extract (1-based)
            
        Returns:
            Dict[str, Any]: Page content including text, tables, and images
        """
        pass 