from typing import Dict, List, Any, Optional
import re
from .base import BaseExtractor

class GeneralExtractor(BaseExtractor):
    """General-purpose extractor for various types of PDFs."""
    
    # Common patterns for general document elements
    PATTERNS = {
        'date': r'\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b',
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'phone': r'\b(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
        'url': r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+',
        'currency': r'\$\s*\d+(?:,\d{3})*(?:\.\d{2})?|\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:USD|EUR|GBP)',
        'percentage': r'\b\d+(?:\.\d+)?%\b',
        'number': r'\b\d+(?:,\d{3})*(?:\.\d+)?\b',
        'heading': r'^(?:[A-Z][A-Za-z\s]+)(?::|\.|\n)',
        'list_item': r'^(?:\d+\.|\*|\-|\•)\s+[A-Za-z]',
        'table_header': r'^(?:[A-Z][A-Za-z\s]+(?:\t|\s{2,})[A-Z][A-Za-z\s]+)+$'
    }
    
    def extract(self, **kwargs) -> Dict[str, Any]:
        """Extract data from any PDF document.
        
        Returns:
            Dict[str, Any]: Extracted document data
        """
        text = self.parser.extract_text()
        metadata = self.parser.extract_metadata()
        
        # Extract document structure and content
        results = {
            'metadata': metadata,
            'document_info': self._extract_document_info(text),
            'content_structure': self._extract_structure(text),
            'tables': self._extract_tables(),
            'lists': self._extract_lists(text),
            'references': self._extract_references(text),
            'contact_info': self._extract_contact_info(text)
        }
        
        return results
    
    def _extract_document_info(self, text: str) -> Dict[str, Any]:
        """Extract basic document information."""
        info = {
            'dates': self.find_pattern(self.PATTERNS['date'], text),
            'emails': self.find_pattern(self.PATTERNS['email'], text),
            'urls': self.find_pattern(self.PATTERNS['url'], text),
            'currencies': self.find_pattern(self.PATTERNS['currency'], text),
            'percentages': self.find_pattern(self.PATTERNS['percentage'], text)
        }
        return {k: v for k, v in info.items() if v}  # Remove empty lists
    
    def _extract_structure(self, text: str) -> Dict[str, Any]:
        """Extract document structure including headings and sections."""
        structure = {
            'headings': [],
            'sections': []
        }
        
        # Split text into lines and process
        lines = text.split('\n')
        current_section = []
        current_heading = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check for heading
            heading_match = re.match(self.PATTERNS['heading'], line)
            if heading_match:
                # Save previous section if exists
                if current_heading and current_section:
                    structure['sections'].append({
                        'heading': current_heading,
                        'content': '\n'.join(current_section)
                    })
                current_heading = heading_match.group(0).rstrip(':.')
                structure['headings'].append(current_heading)
                current_section = []
            else:
                current_section.append(line)
        
        # Add the last section
        if current_heading and current_section:
            structure['sections'].append({
                'heading': current_heading,
                'content': '\n'.join(current_section)
            })
        
        return structure
    
    def _extract_tables(self) -> List[Dict[str, Any]]:
        """Extract and validate tables from the document."""
        tables = []
        table_data = self.parser.extract_tables()
        
        for table in table_data:
            if not table['table'] or len(table['table']) < 2:
                continue
                
            # Clean and validate table
            cleaned_table = []
            headers = []
            
            # Process headers
            if table['table'][0]:
                headers = [str(h).strip() for h in table['table'][0] if h]
            
            # Process rows
            for row in table['table'][1:]:
                if not row:
                    continue
                    
                # Clean row values
                cleaned_row = [str(cell).strip() if cell is not None else '' for cell in row]
                
                # Skip empty rows
                if any(cell for cell in cleaned_row):
                    # If we have headers, create a dictionary
                    if headers and len(headers) == len(cleaned_row):
                        row_dict = dict(zip(headers, cleaned_row))
                        cleaned_table.append(row_dict)
                    else:
                        cleaned_table.append(cleaned_row)
            
            if cleaned_table:
                tables.append({
                    'page': table['page'],
                    'headers': headers if headers else None,
                    'data': cleaned_table,
                    'bbox': table.get('bbox')
                })
        
        return tables
    
    def _extract_lists(self, text: str) -> List[Dict[str, Any]]:
        """Extract lists from the document."""
        lists = []
        current_list = []
        current_list_type = None
        
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            # Check for list item
            list_match = re.match(self.PATTERNS['list_item'], line)
            if list_match:
                # Save previous list if exists
                if current_list:
                    lists.append({
                        'type': current_list_type,
                        'items': current_list
                    })
                
                # Start new list
                current_list = []
                if line.startswith(('*', '-', '•')):
                    current_list_type = 'bullet'
                else:
                    current_list_type = 'numbered'
                
                # Add item without the marker
                item = re.sub(r'^(?:\d+\.|\*|\-|\•)\s+', '', line)
                current_list.append(item)
            elif current_list:
                # Continue current list
                current_list.append(line)
        
        # Add the last list
        if current_list:
            lists.append({
                'type': current_list_type,
                'items': current_list
            })
        
        return lists
    
    def _extract_references(self, text: str) -> List[Dict[str, str]]:
        """Extract references and citations from the document."""
        references = []
        
        # Look for common reference patterns
        ref_patterns = [
            r'\[\d+\].*?(?=\[\d+\]|$)',  # [1] style
            r'\(\d{4}\)[^)]*',  # (2023) style
            r'[A-Z][a-z]+ et al\., \d{4}',  # Author et al., 2023 style
            r'https?://[^\s]+'  # URLs
        ]
        
        for pattern in ref_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                ref_text = match.group(0).strip()
                if ref_text:
                    # Try to extract URL if present
                    url_match = re.search(self.PATTERNS['url'], ref_text)
                    references.append({
                        'text': ref_text,
                        'url': url_match.group(0) if url_match else None
                    })
        
        return references
    
    def _extract_contact_info(self, text: str) -> Dict[str, List[str]]:
        """Extract contact information from the document."""
        contact_info = {
            'emails': self.find_pattern(self.PATTERNS['email'], text),
            'phones': self.find_pattern(self.PATTERNS['phone'], text),
            'urls': self.find_pattern(self.PATTERNS['url'], text)
        }
        return {k: v for k, v in contact_info.items() if v}  # Remove empty lists 