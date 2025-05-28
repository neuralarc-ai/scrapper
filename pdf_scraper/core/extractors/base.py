from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import re
from ..parsers.base import BaseParser

class BaseExtractor(ABC):
    """Base class for data extractors."""
    
    def __init__(self, parser: BaseParser):
        """Initialize extractor with a PDF parser.
        
        Args:
            parser: Instance of a PDF parser
        """
        self.parser = parser
    
    @abstractmethod
    def extract(self, **kwargs) -> Dict[str, Any]:
        """Extract data from the PDF according to specific rules.
        
        Args:
            **kwargs: Additional parameters for extraction
            
        Returns:
            Dict[str, Any]: Extracted data
        """
        pass
    
    def find_pattern(self, pattern: str, text: str) -> List[str]:
        """Find all occurrences of a regex pattern in text.
        
        Args:
            pattern: Regular expression pattern
            text: Text to search in
            
        Returns:
            List[str]: List of matched strings
        """
        return re.findall(pattern, text)
    
    def extract_tables_by_keyword(self, keyword: str) -> List[Dict[str, Any]]:
        """Extract tables that contain a specific keyword.
        
        Args:
            keyword: Keyword to search for in tables
            
        Returns:
            List[Dict[str, Any]]: List of matching tables with metadata
        """
        tables = self.parser.extract_tables()
        matching_tables = []
        
        for table_data in tables:
            table = table_data["table"]
            # Flatten table and search for keyword
            flat_table = [str(cell) for row in table for cell in row]
            if any(keyword.lower() in str(cell).lower() for cell in flat_table):
                matching_tables.append(table_data)
        
        return matching_tables
    
    def extract_text_by_section(self, section_header: str) -> Optional[str]:
        """Extract text from a specific section of the document.
        
        Args:
            section_header: Header text that marks the start of the section
            
        Returns:
            Optional[str]: Section text if found, None otherwise
        """
        text = self.parser.extract_text()
        sections = text.split('\n\n')
        
        for i, section in enumerate(sections):
            if section_header.lower() in section.lower():
                # Return the next section if it exists
                if i + 1 < len(sections):
                    return sections[i + 1].strip()
                return section.strip()
        
        return None 