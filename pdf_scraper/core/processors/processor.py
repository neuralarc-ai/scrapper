import os
import json
import pandas as pd
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from ..parsers.pdfplumber_parser import PDFPlumberParser
from ..extractors.base import BaseExtractor

class PDFProcessor:
    """Main processor class for handling PDF extraction and output formatting."""
    
    def __init__(self, extractor_class: type[BaseExtractor]):
        """Initialize processor with an extractor class.
        
        Args:
            extractor_class: Class of the extractor to use
        """
        self.extractor_class = extractor_class
    
    def process_file(self, file_path: str) -> Dict[str, Any]:
        """Process a single PDF file.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Dict[str, Any]: Extracted data
        """
        parser = PDFPlumberParser(file_path)
        extractor = self.extractor_class(parser)
        return extractor.extract()
    
    def process_directory(self, directory: str, recursive: bool = False) -> List[Dict[str, Any]]:
        """Process all PDF files in a directory.
        
        Args:
            directory: Path to directory containing PDFs
            recursive: Whether to process subdirectories
            
        Returns:
            List[Dict[str, Any]]: List of extracted data from each PDF
        """
        results = []
        path = Path(directory)
        
        # Get all PDF files
        if recursive:
            pdf_files = list(path.rglob("*.pdf"))
        else:
            pdf_files = list(path.glob("*.pdf"))
        
        # Process each file
        for pdf_file in pdf_files:
            try:
                result = self.process_file(str(pdf_file))
                result['file_name'] = pdf_file.name
                results.append(result)
            except Exception as e:
                print(f"Error processing {pdf_file}: {str(e)}")
        
        return results
    
    def export_json(self, data: Union[Dict[str, Any], List[Dict[str, Any]]], output_path: str):
        """Export data to JSON format.
        
        Args:
            data: Data to export
            output_path: Path to save JSON file
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def export_csv(self, data: List[Dict[str, Any]], output_path: str):
        """Export data to CSV format.
        
        Args:
            data: List of data to export
            output_path: Path to save CSV file
        """
        # Flatten nested dictionaries
        flattened_data = []
        for item in data:
            flat_item = {}
            for key, value in item.items():
                if isinstance(value, dict):
                    for subkey, subvalue in value.items():
                        flat_item[f"{key}_{subkey}"] = subvalue
                elif isinstance(value, list):
                    flat_item[key] = "; ".join(str(v) for v in value)
                else:
                    flat_item[key] = value
            flattened_data.append(flat_item)
        
        df = pd.DataFrame(flattened_data)
        df.to_csv(output_path, index=False)
    
    def export_excel(self, data: List[Dict[str, Any]], output_path: str):
        """Export data to Excel format.
        
        Args:
            data: List of data to export
            output_path: Path to save Excel file
        """
        # Create a Pandas Excel writer
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Export main data
            df = pd.DataFrame(data)
            df.to_excel(writer, sheet_name='Main Data', index=False)
            
            # Export nested data in separate sheets if present
            for item in data:
                for key, value in item.items():
                    if isinstance(value, dict):
                        df_nested = pd.DataFrame([value])
                        df_nested.to_excel(writer, sheet_name=key[:31], index=False)
    
    def export_text(self, data: Union[Dict[str, Any], List[Dict[str, Any]]], output_path: str):
        """Export data to plain text format.
        
        Args:
            data: Data to export
            output_path: Path to save text file
        """
        def format_item(item: Dict[str, Any], indent: int = 0) -> str:
            result = []
            for key, value in item.items():
                if isinstance(value, dict):
                    result.append(f"{' ' * indent}{key}:")
                    result.append(format_item(value, indent + 2))
                elif isinstance(value, list):
                    result.append(f"{' ' * indent}{key}:")
                    for v in value:
                        if isinstance(v, dict):
                            result.append(format_item(v, indent + 2))
                        else:
                            result.append(f"{' ' * (indent + 2)}- {v}")
                else:
                    result.append(f"{' ' * indent}{key}: {value}")
            return "\n".join(result)
        
        if isinstance(data, list):
            text = "\n\n".join(format_item(item) for item in data)
        else:
            text = format_item(data)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text) 