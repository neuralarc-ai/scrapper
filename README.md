# Universal PDF Search & Scraper

A powerful tool for searching and extracting PDF documents from the web based on any topic or requirement.

## Features

- General-purpose web search for **PDF documents** using Google Custom Search API
- Extract titles, snippets, and URLs of PDF files from search results
- (Limited) Summarization of web pages (primarily HTML, may not work for all PDFs)
- User-friendly web interface
- Export results in multiple formats (JSON, CSV)
- Configurable search parameters

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd web-research-scraper
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. **Configure Google API Credentials:**
   - Obtain your Google API Key and Custom Search Engine (CSE) ID by following steps 4a-4d in the previous version of the README.
   - Create a file named `.env` in the root directory of the project (at `/Users/admin/Desktop/scrapping`).
   - Add the following lines to the `.env` file, replacing the placeholder values with your actual credentials:

   ```
   GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY"
   GOOGLE_CSE_ID="YOUR_GOOGLE_CSE_ID"
   ```

   - **Make sure to add `.env` to your `.gitignore` file** if you are using Git for version control to prevent your credentials from being committed.

## Usage

### Web Interface

1. Start the Streamlit app:
```bash
streamlit run pdf_scraper/web_app.py
```

2. Open your browser and navigate to the provided URL (usually http://localhost:8501)

3. The app will automatically load your API key and CSE ID from the `.env` file. Simply use the interface to:
   - Enter your search query.
   - Adjust the maximum number of results (up to 100).
   - View and download the results (which will be links to PDF files).
   - Click on the "Download PDF" link in the detailed view to open the PDF.

### Command Line Interface

The scraper can also be used programmatically:

```python
from pdf_scraper.core.scrapers.general import GeneralWebScraper
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get credentials
API_KEY = os.getenv("GOOGLE_API_KEY")
CSE_ID = os.getenv("GOOGLE_CSE_ID")

# Initialize the scraper with your credentials
# It is configured to specifically search for PDF files.
if API_KEY and CSE_ID:
    scraper = GeneralWebScraper(api_key=API_KEY, cse_id=CSE_ID)

    # Search for PDF documents
    results = scraper.search(
        query="deep learning research papers",
        max_results=15
    )

    # Print results (links to PDFs)
    for result in results:
        print(f"Title: {result['title']}")
        print(f"PDF URL: {result['url']}")
        print("---")

else:
    print("Google API Key or CSE ID not found in environment variables.")
```

## Output Format

The search returns data in the following format (specifically for PDF results):

```python
[
  {
    'title': 'PDF Document Title',
    'snippet': 'Brief description of the PDF content.',
    'url': 'URL of the PDF file'
  },
  ...
]
```

The `extract_data` method for a specific URL returns (with limitations for PDFs):

```python
{
  'url': 'URL of the page',
  'summary': 'Summary of the page content'
}
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Google Custom Search API
- BeautifulSoup4 for HTML parsing (for summarization)
- Streamlit for the web interface
- Requests for HTTP requests
- python-dotenv for loading environment variables
- All the open-source libraries used in this project. 