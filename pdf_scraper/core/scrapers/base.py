from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import requests
from bs4 import BeautifulSoup
import json
import time
from urllib.parse import urljoin

class BaseScraper(ABC):
    """Base class for web scrapers."""
    
    def __init__(self):
        """Initialize the scraper with common attributes."""
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.session.headers.update(self.headers)
    
    @abstractmethod
    def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """Search for data based on the query.
        
        Args:
            query: Search query
            **kwargs: Additional search parameters
            
        Returns:
            List[Dict[str, Any]]: List of search results
        """
        pass
    
    @abstractmethod
    def extract_data(self, url: str, **kwargs) -> Dict[str, Any]:
        """Extract data from a specific URL.
        
        Args:
            url: URL to extract data from
            **kwargs: Additional extraction parameters
            
        Returns:
            Dict[str, Any]: Extracted data
        """
        pass
    
    def get_page(self, url: str) -> Optional[BeautifulSoup]:
        """Get and parse a web page.
        
        Args:
            url: URL to fetch
            
        Returns:
            Optional[BeautifulSoup]: Parsed page content or None if failed
        """
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            print(f"Error fetching {url}: {str(e)}")
            return None
    
    def extract_links(self, soup: BeautifulSoup, base_url: str, pattern: str = None) -> List[str]:
        """Extract links from a page.
        
        Args:
            soup: BeautifulSoup object of the page
            base_url: Base URL for resolving relative links
            pattern: Optional regex pattern to filter links
            
        Returns:
            List[str]: List of extracted links
        """
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if pattern and not re.search(pattern, href):
                continue
            full_url = urljoin(base_url, href)
            links.append(full_url)
        return links
    
    def extract_text(self, soup: BeautifulSoup, selector: str) -> Optional[str]:
        """Extract text from an element.
        
        Args:
            soup: BeautifulSoup object
            selector: CSS selector for the element
            
        Returns:
            Optional[str]: Extracted text or None if not found
        """
        element = soup.select_one(selector)
        return element.get_text(strip=True) if element else None
    
    def extract_metadata(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract metadata from a page.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            Dict[str, str]: Extracted metadata
        """
        metadata = {}
        
        # Extract title
        title = soup.find('title')
        if title:
            metadata['title'] = title.get_text(strip=True)
        
        # Extract meta tags
        for meta in soup.find_all('meta'):
            name = meta.get('name', meta.get('property', ''))
            content = meta.get('content', '')
            if name and content:
                metadata[name] = content
        
        return metadata
    
    def save_results(self, data: List[Dict[str, Any]], filename: str):
        """Save results to a file.
        
        Args:
            data: Data to save
            filename: Output filename
        """
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def __del__(self):
        """Clean up resources."""
        self.session.close() 