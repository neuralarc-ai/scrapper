import pdfplumber
from typing import Dict, List, Any
from .base import BaseParser

class PDFPlumberParser(BaseParser):
    """PDF parser implementation using pdfplumber."""
    
    def __init__(self, file_path: str):
        super().__init__(file_path)
        self.pdf = pdfplumber.open(file_path)
    
    def extract_text(self) -> str:
        """Extract all text from the PDF using pdfplumber with improved layout handling."""
        text_sections = []
        
        for page in self.pdf.pages:
            # Extract text with layout preservation
            words = page.extract_words(
                keep_blank_chars=False,
                x_tolerance=3,  # Adjust for slight misalignments
                y_tolerance=3,
                use_text_flow=True  # Maintain reading order
            )
            
            if not words:
                continue
                
            # Group words into lines based on y-coordinate
            current_line = []
            current_y = words[0]['top']
            page_text = []
            
            for word in words:
                # If word is significantly below current line, start new line
                if word['top'] - current_y > 5:  # 5 points threshold for new line
                    if current_line:
                        page_text.append(' '.join(current_line))
                        current_line = []
                    current_y = word['top']
                
                current_line.append(word['text'])
            
            # Add the last line
            if current_line:
                page_text.append(' '.join(current_line))
            
            # Join lines with proper spacing
            text_sections.append('\n'.join(page_text))
        
        # Join pages with double newlines to clearly separate sections
        return '\n\n'.join(text_sections)
    
    def extract_tables(self) -> List[Dict[str, Any]]:
        """Extract tables from the PDF using pdfplumber with improved table detection."""
        tables = []
        
        for i, page in enumerate(self.pdf.pages, 1):
            # Extract tables with improved settings
            page_tables = page.extract_tables({
                'vertical_strategy': 'text',  # Use text position for vertical lines
                'horizontal_strategy': 'text',  # Use text position for horizontal lines
                'intersection_tolerance': 3,  # Allow slight misalignments
                'snap_tolerance': 3,  # Snap lines to nearby text
                'join_tolerance': 3,  # Join nearby lines
                'edge_min_length': 3,  # Minimum length for table edges
                'min_words_vertical': 3,  # Minimum words for vertical lines
                'min_words_horizontal': 3  # Minimum words for horizontal lines
            })
            
            if page_tables:
                for table in page_tables:
                    # Clean and validate table
                    cleaned_table = []
                    for row in table:
                        # Clean cell values
                        cleaned_row = [
                            str(cell).strip() if cell is not None else ''
                            for cell in row
                        ]
                        # Skip empty rows
                        if any(cell for cell in cleaned_row):
                            cleaned_table.append(cleaned_row)
                    
                    # Only add tables with at least 2 rows and 2 columns
                    if len(cleaned_table) >= 2 and len(cleaned_table[0]) >= 2:
                        tables.append({
                            "page": i,
                            "table": cleaned_table,
                            "bbox": page.bbox  # Add bounding box for context
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
        """Extract content from a specific page with improved structure."""
        if not 1 <= page_number <= len(self.pdf.pages):
            raise ValueError(f"Page number {page_number} out of range")
        
        page = self.pdf.pages[page_number - 1]
        
        # Extract text with layout preservation
        words = page.extract_words(
            keep_blank_chars=False,
            x_tolerance=3,
            y_tolerance=3,
            use_text_flow=True
        )
        
        # Group text into sections based on spacing
        sections = []
        current_section = []
        current_y = words[0]['top'] if words else 0
        
        for word in words:
            # If word is significantly below current section, start new section
            if word['top'] - current_y > 10:  # 10 points threshold for new section
                if current_section:
                    sections.append(' '.join(current_section))
                    current_section = []
                current_y = word['top']
            
            current_section.append(word['text'])
        
        # Add the last section
        if current_section:
            sections.append(' '.join(current_section))
        
        return {
            "text": '\n\n'.join(sections),
            "tables": self.extract_tables(),  # Use the improved table extraction
            "images": [img for img in page.images],
            "width": page.width,
            "height": page.height,
            "page_number": page_number
        }
    
    def __del__(self):
        """Close the PDF file when the parser is destroyed."""
        if hasattr(self, 'pdf'):
            self.pdf.close() 