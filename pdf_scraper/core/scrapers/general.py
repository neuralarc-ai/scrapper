import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from googleapiclient.discovery import build
from .base import BaseScraper
import streamlit as st
import re
from urllib.parse import urlparse

class GeneralWebScraper(BaseScraper):
    """Web scraper focused on trusted dataset repositories."""
    
    # Trusted dataset repositories with their specific endpoints and access patterns
    DATASET_SOURCES = {
        'government': {
            'data.gov': {
                'base_url': 'https://catalog.data.gov',
                'search_pattern': '/dataset?q={query}',
                'access_type': 'open',
                'description': 'US Government Open Data'
            },
            'data.europa.eu': {
                'base_url': 'https://data.europa.eu',
                'search_pattern': '/en/data/search?q={query}',
                'access_type': 'open',
                'description': 'EU Open Data Portal'
            },
            'ukdataservice.ac.uk': {
                'base_url': 'https://ukdataservice.ac.uk',
                'search_pattern': '/find-data/search-results?q={query}',
                'access_type': 'mixed',
                'description': 'UK Data Service'
            },
            'open.canada.ca': {
                'base_url': 'https://open.canada.ca',
                'search_pattern': '/en/search?q={query}',
                'access_type': 'open',
                'description': 'Canada Open Government Data'
            },
            'data.gov.au': {
                'base_url': 'https://data.gov.au',
                'search_pattern': '/search?q={query}',
                'access_type': 'open',
                'description': 'Australian Government Data'
            }
        },
        'academic': {
            'archive.ics.uci.edu': {
                'base_url': 'https://archive.ics.uci.edu',
                'search_pattern': '/ml/datasets.php?search={query}',
                'access_type': 'open',
                'description': 'UCI Machine Learning Repository'
            },
            'dataverse.harvard.edu': {
                'base_url': 'https://dataverse.harvard.edu',
                'search_pattern': '/search?q={query}',
                'access_type': 'open',
                'description': 'Harvard Dataverse'
            },
            'github.com/fivethirtyeight/data': {
                'base_url': 'https://github.com/fivethirtyeight/data',
                'search_pattern': '/search?q={query}',
                'access_type': 'open',
                'description': 'FiveThirtyEight Data'
            }
        },
        'international': {
            'data.worldbank.org': {
                'base_url': 'https://data.worldbank.org',
                'search_pattern': '/search?q={query}',
                'access_type': 'open',
                'description': 'World Bank Open Data'
            },
            'data.un.org': {
                'base_url': 'https://data.un.org',
                'search_pattern': '/Search.aspx?q={query}',
                'access_type': 'open',
                'description': 'UN Data'
            },
            'data.imf.org': {
                'base_url': 'https://data.imf.org',
                'search_pattern': '/search?q={query}',
                'access_type': 'open',
                'description': 'IMF Data Portal'
            }
        },
        'specialized': {
            'climate.noaa.gov': {
                'base_url': 'https://www.ncdc.noaa.gov',
                'search_pattern': '/cdo-web/search?q={query}',
                'access_type': 'open',
                'description': 'NOAA Climate Data'
            },
            'download.geofabrik.de': {
                'base_url': 'https://download.geofabrik.de',
                'search_pattern': '/index.html',
                'access_type': 'open',
                'description': 'OpenStreetMap Geofabrik Extracts'
            },
            'github.com/CSSEGISandData/COVID-19': {
                'base_url': 'https://github.com/CSSEGISandData/COVID-19',
                'search_pattern': '/search?q={query}',
                'access_type': 'open',
                'description': 'COVID-19 Dataset'
            },
            'vincentarelbundock.github.io/Rdatasets': {
                'base_url': 'https://vincentarelbundock.github.io/Rdatasets',
                'search_pattern': '/datasets.html',
                'access_type': 'open',
                'description': 'R Project Datasets'
            }
        }
    }

    def __init__(self, api_key: str, cse_id: str):
        super().__init__()
        self.api_key = api_key
        self.cse_id = cse_id
        self.service = build("customsearch", "v1", developerKey=self.api_key)
        
    def _get_source_info(self, url: str) -> dict:
        """Get detailed information about a dataset source."""
        domain = urlparse(url).netloc.lower()
        
        for category, sources in self.DATASET_SOURCES.items():
            for source_domain, info in sources.items():
                if source_domain in domain:
                    return {
                        'category': category,
                        'source': source_domain,
                        'access_type': info['access_type'],
                        'description': info['description'],
                        'base_url': info['base_url']
                    }
        
        return {
            'category': 'unknown',
            'source': domain,
            'access_type': 'unknown',
            'description': 'Unknown source',
            'base_url': None
        }

    def _construct_search_url(self, source_info: dict, query: str) -> str:
        """Construct a search URL for a specific dataset source."""
        if not source_info['base_url']:
            return None
            
        search_pattern = self.DATASET_SOURCES.get(source_info['category'], {}).get(source_info['source'], {}).get('search_pattern')
        if not search_pattern:
            return None
            
        return source_info['base_url'] + search_pattern.format(query=query)

    def search(self, query: str) -> List[Dict[str, Any]]:
        """Search for datasets across trusted repositories.
        
        Args:
            query: Search query
            
        Returns:
            List[Dict[str, Any]]: List of search results (datasets)
        """
        results = []
        try:
            # Format query for dataset search
            formatted_queries = [
                f'"{query}" dataset',  # Exact match
                f'"{query}" data',     # Data files
                query + ' dataset'     # Broader search
            ]
            
            for search_query in formatted_queries:
                # First try direct repository searches
                for category, sources in self.DATASET_SOURCES.items():
                    for source_domain, info in sources.items():
                        source_info = {
                            'category': category,
                            'source': source_domain,
                            'access_type': info['access_type'],
                            'description': info['description'],
                            'base_url': info['base_url']
                        }
                        
                        search_url = self._construct_search_url(source_info, search_query)
                        if search_url:
                            try:
                                # Add source-specific search results
                                source_results = self._search_with_query(
                                    search_query,
                                    site=source_domain,
                                    additional_params={'source': source_info}
                                )
                                if source_results:
                                    results.extend(source_results)
                            except Exception as e:
                                print(f"Error searching {source_domain}: {e}")
                
                # Then try Google Custom Search as fallback
                if len(results) < 10:  # If we don't have enough results
                    google_results = self._search_with_query(
                        search_query,
                        additional_params={'prefer_direct': True}
                    )
                    if google_results:
                        results.extend(google_results)
            
            # Filter and rank results
            filtered_results = []
            seen_urls = set()
            
            for result in results:
                url = result.get('url', '').lower()
                title = result.get('title', '').lower()
                snippet = result.get('snippet', '').lower()
                
                # Skip if we've seen this URL before
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                
                # Get source information
                source_info = self._get_source_info(url)
                
                # Calculate relevance score
                score = 0
                query_terms = query.lower().split()
                
                # Base score for trusted sources
                if source_info['category'] != 'unknown':
                    score += 50
                    if source_info['category'] == 'government':
                        score += 30
                    elif source_info['category'] == 'academic':
                        score += 25
                    elif source_info['category'] == 'international':
                        score += 20
                    elif source_info['category'] == 'specialized':
                        score += 15
                
                # Title exact match
                if all(term in title for term in query_terms):
                    score += 40
                
                # Title partial match
                score += sum(10 for term in query_terms if term in title)
                
                # Snippet match
                score += sum(5 for term in query_terms if term in snippet)
                
                # Add metadata
                result.update({
                    'relevance_score': score,
                    'source_category': source_info['category'],
                    'source_name': source_info['source'],
                    'source_description': source_info['description'],
                    'access_type': source_info['access_type'],
                    'base_url': source_info['base_url']
                })
                
                filtered_results.append(result)
            
            # Sort by relevance score and take top results
            filtered_results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
            return filtered_results[:20]  # Return top 20 most relevant results
                    
        except Exception as e:
            print(f"Error during search: {e}")
            return []

    def _search_with_query(self, query: str, site: str = None, additional_params: dict = None) -> List[Dict[str, Any]]:
        """Helper method to perform a search with given query and parameters."""
        results = []
        try:
            # Google Custom Search API parameters
            params = {
                'q': query,
                'cx': self.cse_id,
                'num': 10,
                'fileType': 'csv,json,xlsx,xls,zip',  # Common dataset file types
                'safe': 'off'
            }
            
            if site:
                params['q'] = f'site:{site} {query}'
            
            if additional_params and additional_params.get('prefer_direct'):
                # Add file type restrictions for direct dataset files
                params['q'] += ' (filetype:csv OR filetype:json OR filetype:xlsx OR filetype:xls OR filetype:zip)'
            
            # Execute search
            search_results = self.service.cse().list(**params).execute()
            
            if 'items' in search_results:
                for item in search_results['items']:
                    url = item.get('link')
                    if url:
                        result = {
                            "title": item.get('title', ''),
                            "snippet": item.get('snippet', ''),
                            "url": url,
                            "source": item.get('displayLink', '')
                        }
                        
                        # Add any additional parameters
                        if additional_params:
                            result.update(additional_params)
                            
                        results.append(result)
                        
        except Exception as e:
            print(f"Error during search with query '{query}': {e}")
            
        return results

    def extract_data(self, url: str, **kwargs) -> Dict[str, Any]:
        """Fetch and verify dataset content.
        
        Args:
            url: URL to fetch
            **kwargs: Additional extraction parameters
            
        Returns:
            Dict[str, Any]: Extracted data including verification status
        """
        try:
            # Get source information
            source_info = self._get_source_info(url)
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9'
            }
            
            response = requests.get(url, headers=headers, timeout=10, verify=False)
            
            # Check for authentication requirements
            if response.status_code == 403:
                return {
                    "url": url,
                    "status": "restricted",
                    "error": "Access restricted. This resource may require authentication.",
                    "source_info": source_info
                }
            
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            file_size = len(response.content)
            
            # Common dataset file types
            dataset_types = {
                'csv': 'text/csv',
                'json': 'application/json',
                'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'xls': 'application/vnd.ms-excel',
                'zip': 'application/zip'
            }
            
            # Verify if it's a dataset file
            is_dataset = any(t in content_type for t in dataset_types.values())
            file_ext = url.split('.')[-1].lower() if '.' in url else ''
            
            if is_dataset or file_ext in dataset_types:
                return {
                    "url": url,
                    "status": "success",
                    "content_type": content_type,
                    "size": file_size,
                    "file_type": file_ext if file_ext in dataset_types else 'unknown',
                    "source_info": source_info
                }
            else:
                return {
                    "url": url,
                    "status": "error",
                    "error": "Not a recognized dataset file",
                    "content_type": content_type,
                    "source_info": source_info
                }
                
        except requests.exceptions.SSLError:
            return {
                "url": url,
                "status": "error",
                "error": "SSL certificate verification failed",
                "source_info": source_info
            }
        except requests.exceptions.HTTPError as e:
            return {
                "url": url,
                "status": "error",
                "error": f"HTTP error: {str(e)}",
                "source_info": source_info
            }
        except requests.exceptions.ConnectionError:
            return {
                "url": url,
                "status": "error",
                "error": "Connection error",
                "source_info": source_info
            }
        except requests.exceptions.Timeout:
            return {
                "url": url,
                "status": "error",
                "error": "Request timed out",
                "source_info": source_info
            }
        except Exception as e:
            return {
                "url": url,
                "status": "error",
                "error": str(e),
                "source_info": source_info
            } 