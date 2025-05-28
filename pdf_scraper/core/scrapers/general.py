import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from googleapiclient.discovery import build
from .base import BaseScraper
import streamlit as st

class GeneralWebScraper(BaseScraper):
    """General-purpose web scraper using Google Custom Search API for PDFs."""
    def __init__(self, api_key: str, cse_id: str):
        super().__init__()
        self.api_key = api_key
        self.cse_id = cse_id
        self.service = build("customsearch", "v1", developerKey=self.api_key)

    def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search Google using the Custom Search API for PDF files.
        
        Args:
            query: Search query
            max_results: Maximum number of results to return (up to 100 for Google API)
            
        Returns:
            List[Dict[str, Any]]: List of search results (PDFs)
        """
        results = []
        try:
            # Google Custom Search API has a limit of 10 results per page, but supports pagination
            # We'll fetch results in batches of 10 up to max_results
            start_index = 1
            while len(results) < max_results and start_index <= 100:
                search_results = self.service.cse().list(
                    q=query,
                    cx=self.cse_id,
                    num=10, # Fetch 10 results per request
                    start=start_index,
                    fileType='pdf' # Explicitly request PDF files
                ).execute()
                
                if 'items' in search_results:
                    for item in search_results['items']:
                        if len(results) < max_results:
                            results.append({
                                "title": item.get('title'),
                                "snippet": item.get('snippet'),
                                "url": item.get('link')
                            })
                    start_index += 10 # Move to the next page of results
                else:
                    break # No more results found
                    
        except Exception as e:
            print(f"Error during Google Custom Search API call: {e}")
        return results

    def extract_data(self, url: str, **kwargs) -> Dict[str, Any]:
        """Fetch and summarize the content of a web page.
        
        Args:
            url: URL to fetch
            **kwargs: Additional extraction parameters
            
        Returns:
            Dict[str, Any]: Extracted data including summary
        """
        # Note: Summarization might not work well for all PDF links fetched.
        # This method is primarily for HTML pages.
        st.warning("Summarization is primarily for HTML pages and may not work for all PDF links.")
        return {"url": url, "summary": "Summarization not fully supported for PDFs via this method."} 