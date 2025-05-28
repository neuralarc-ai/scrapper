from typing import Dict, List, Any, Optional
import re
from bs4 import BeautifulSoup
from .base import BaseScraper

class MedicalResearchScraper(BaseScraper):
    """Scraper for medical research papers."""
    
    def __init__(self):
        super().__init__()
        self.sources = {
            'pubmed': 'https://pubmed.ncbi.nlm.nih.gov/',
            'scholar': 'https://scholar.google.com/scholar',
            'sciencedirect': 'https://www.sciencedirect.com/search'
        }
    
    def search(self, query: str, source: str = 'pubmed', max_results: int = 10) -> List[Dict[str, Any]]:
        """Search for medical research papers.
        
        Args:
            query: Search query
            source: Source to search from (pubmed, scholar, sciencedirect)
            max_results: Maximum number of results to return
            
        Returns:
            List[Dict[str, Any]]: List of search results
        """
        if source not in self.sources:
            raise ValueError(f"Invalid source. Must be one of: {', '.join(self.sources.keys())}")
        
        search_url = self.sources[source]
        results = []
        
        if source == 'pubmed':
            results = self._search_pubmed(query, max_results)
        elif source == 'scholar':
            results = self._search_scholar(query, max_results)
        elif source == 'sciencedirect':
            results = self._search_sciencedirect(query, max_results)
        
        return results
    
    def _search_pubmed(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Search PubMed for medical papers."""
        results = []
        search_url = f"{self.sources['pubmed']}?term={query}&size={max_results}"
        
        soup = self.get_page(search_url)
        if not soup:
            return results
        
        for article in soup.select('.docsum-wrap'):
            try:
                title = self.extract_text(article, '.docsum-title')
                authors = self.extract_text(article, '.docsum-authors')
                journal = self.extract_text(article, '.docsum-journal')
                date = self.extract_text(article, '.docsum-date')
                pmid = article.get('data-pmid', '')
                
                if title:
                    results.append({
                        'title': title,
                        'authors': authors,
                        'journal': journal,
                        'date': date,
                        'pmid': pmid,
                        'url': f"{self.sources['pubmed']}{pmid}/"
                    })
            except Exception as e:
                print(f"Error parsing article: {str(e)}")
        
        return results
    
    def _search_scholar(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Search Google Scholar for medical papers."""
        results = []
        search_url = f"{self.sources['scholar']}?q={query}&num={max_results}"
        
        soup = self.get_page(search_url)
        if not soup:
            return results
        
        for article in soup.select('.gs_ri'):
            try:
                title = self.extract_text(article, '.gs_rt')
                authors = self.extract_text(article, '.gs_a')
                abstract = self.extract_text(article, '.gs_rs')
                citations = self.extract_text(article, '.gs_fl')
                
                if title:
                    results.append({
                        'title': title,
                        'authors': authors,
                        'abstract': abstract,
                        'citations': citations,
                        'url': article.select_one('.gs_rt a')['href'] if article.select_one('.gs_rt a') else None
                    })
            except Exception as e:
                print(f"Error parsing article: {str(e)}")
        
        return results
    
    def _search_sciencedirect(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Search ScienceDirect for medical papers."""
        results = []
        search_url = f"{self.sources['sciencedirect']}?qs={query}&limit={max_results}"
        
        soup = self.get_page(search_url)
        if not soup:
            return results
        
        for article in soup.select('.ResultItem'):
            try:
                title = self.extract_text(article, '.text-s')
                authors = self.extract_text(article, '.author-name')
                journal = self.extract_text(article, '.publication-title')
                date = self.extract_text(article, '.publication-date')
                
                if title:
                    results.append({
                        'title': title,
                        'authors': authors,
                        'journal': journal,
                        'date': date,
                        'url': article.select_one('a')['href'] if article.select_one('a') else None
                    })
            except Exception as e:
                print(f"Error parsing article: {str(e)}")
        
        return results
    
    def extract_data(self, url: str, **kwargs) -> Dict[str, Any]:
        """Extract detailed data from a paper URL.
        
        Args:
            url: URL of the paper
            **kwargs: Additional extraction parameters
            
        Returns:
            Dict[str, Any]: Extracted paper data
        """
        soup = self.get_page(url)
        if not soup:
            return {}
        
        # Extract basic metadata
        metadata = self.extract_metadata(soup)
        
        # Extract paper-specific data
        data = {
            'metadata': metadata,
            'abstract': self._extract_abstract(soup),
            'keywords': self._extract_keywords(soup),
            'references': self._extract_references(soup),
            'figures': self._extract_figures(soup)
        }
        
        return data
    
    def _extract_abstract(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract paper abstract."""
        abstract = self.extract_text(soup, '.abstract')
        if not abstract:
            abstract = self.extract_text(soup, '[class*="abstract"]')
        return abstract
    
    def _extract_keywords(self, soup: BeautifulSoup) -> List[str]:
        """Extract paper keywords."""
        keywords = []
        keyword_elements = soup.select('.keyword')
        if not keyword_elements:
            keyword_elements = soup.select('[class*="keyword"]')
        
        for element in keyword_elements:
            keyword = element.get_text(strip=True)
            if keyword:
                keywords.append(keyword)
        
        return keywords
    
    def _extract_references(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract paper references."""
        references = []
        ref_elements = soup.select('.reference')
        if not ref_elements:
            ref_elements = soup.select('[class*="reference"]')
        
        for element in ref_elements:
            try:
                ref_text = element.get_text(strip=True)
                ref_link = element.select_one('a')
                ref_url = ref_link['href'] if ref_link else None
                
                if ref_text:
                    references.append({
                        'text': ref_text,
                        'url': ref_url
                    })
            except Exception as e:
                print(f"Error parsing reference: {str(e)}")
        
        return references
    
    def _extract_figures(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract paper figures."""
        figures = []
        figure_elements = soup.select('figure')
        
        for element in figure_elements:
            try:
                caption = self.extract_text(element, 'figcaption')
                img = element.select_one('img')
                img_url = img['src'] if img else None
                
                if caption or img_url:
                    figures.append({
                        'caption': caption,
                        'url': img_url
                    })
            except Exception as e:
                print(f"Error parsing figure: {str(e)}")
        
        return figures 