import typer
from pathlib import Path
from typing import Optional
from core.processors.processor import PDFProcessor
from core.extractors.medical_report import MedicalReportExtractor

app = typer.Typer()

@app.command()
def process(
    input_path: str = typer.Argument(..., help="Path to PDF file or directory"),
    output_path: str = typer.Argument(..., help="Path to save output file"),
    output_format: str = typer.Option("json", help="Output format (json, csv, excel, text)"),
    recursive: bool = typer.Option(False, help="Process subdirectories recursively"),
    template: str = typer.Option("medical", help="Extraction template to use")
):
    """Process PDF files and extract information."""
    # Validate input path
    input_path = Path(input_path)
    if not input_path.exists():
        typer.echo(f"Error: Input path does not exist: {input_path}")
        raise typer.Exit(1)
    
    # Validate output format
    valid_formats = ["json", "csv", "excel", "text"]
    if output_format not in valid_formats:
        typer.echo(f"Error: Invalid output format. Must be one of: {', '.join(valid_formats)}")
        raise typer.Exit(1)
    
    # Select extractor based on template
    extractor_map = {
        "medical": MedicalReportExtractor,
        # Add more templates here
    }
    
    if template not in extractor_map:
        typer.echo(f"Error: Invalid template. Must be one of: {', '.join(extractor_map.keys())}")
        raise typer.Exit(1)
    
    # Initialize processor
    processor = PDFProcessor(extractor_map[template])
    
    try:
        # Process files
        if input_path.is_file():
            if input_path.suffix.lower() != '.pdf':
                typer.echo("Error: Input file must be a PDF")
                raise typer.Exit(1)
            results = processor.process_file(str(input_path))
        else:
            results = processor.process_directory(str(input_path), recursive)
        
        # Export results
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        export_methods = {
            "json": processor.export_json,
            "csv": processor.export_csv,
            "excel": processor.export_excel,
            "text": processor.export_text
        }
        
        export_methods[output_format](results, str(output_path))
        typer.echo(f"Successfully processed and exported results to {output_path}")
        
    except Exception as e:
        typer.echo(f"Error: {str(e)}")
        raise typer.Exit(1)

@app.command()
def list_templates():
    """List available extraction templates."""
    templates = {
        "medical": "Extract medical report data (vitals, lab results, diagnoses, etc.)",
        # Add more templates here
    }
    
    typer.echo("Available templates:")
    for name, description in templates.items():
        typer.echo(f"  {name}: {description}")

if __name__ == "__main__":
    app() 