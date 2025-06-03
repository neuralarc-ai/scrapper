import streamlit as st
import pandas as pd
from core.scrapers.general import GeneralWebScraper
import os
from dotenv import load_dotenv
import time
import requests
from typing import Dict, Any, List
import json
from urllib.parse import urlparse, parse_qs
import re

# Load environment variables
load_dotenv()

# Initialize session state
if 'search_results' not in st.session_state:
    st.session_state.search_results = []
if 'selected_results' not in st.session_state:
    st.session_state.selected_results = []
if 'download_status' not in st.session_state:
    st.session_state.download_status = {}

def initialize_scraper() -> GeneralWebScraper:
    """Initialize the web scraper with API credentials."""
    api_key = os.getenv('GOOGLE_API_KEY')
    cse_id = os.getenv('GOOGLE_CSE_ID')
    
    if not api_key or not cse_id:
        st.error("Missing API credentials. Please set GOOGLE_API_KEY and GOOGLE_CSE_ID in .env file")
        st.stop()
    
    return GeneralWebScraper(api_key=api_key, cse_id=cse_id)

def display_dataset_info(result: Dict[str, Any]) -> None:
    """Display detailed information about a dataset."""
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown(f"### [{result['title']}]({result['url']})")
        st.markdown(result['snippet'])
        
        # Display source information
        source_info = result.get('source_info', {})
        if source_info.get('category') != 'unknown':
            st.success(f"✅ {source_info.get('description', 'Trusted Dataset Source')}")
            st.info(f"Source: {source_info.get('source', 'Unknown')} ({source_info.get('category', 'Unknown')})")
        else:
            st.warning("⚠️ Source not verified")
        
        # Display file type if available
        if result.get('file_type'):
            st.info(f"📊 File Type: {result['file_type'].upper()}")
    
    with col2:
        # Display relevance score
        score = result.get('relevance_score', 0)
        st.metric("Relevance Score", f"{score:.1f}")
        
        # Add to selection
        if st.button("Select Dataset", key=f"select_{result['url']}"):
            if result['url'] not in [r['url'] for r in st.session_state.selected_results]:
                st.session_state.selected_results.append(result)
                st.success("Dataset added to selection!")
            else:
                st.warning("Dataset already selected!")

def display_search_results(results: List[Dict[str, Any]]) -> None:
    """Display search results with filtering options."""
    if not results:
        st.info("No datasets found. Try adjusting your search terms.")
        return
    
    # Filter options
    st.sidebar.markdown("### Filter Results")
    
    # Source category filter
    categories = ['All'] + list(set(r.get('source_category', 'Unknown') for r in results if r.get('source_category')))
    selected_category = st.sidebar.selectbox("Source Category", categories)
    
    # File type filter
    file_types = ['All'] + list(set(r.get('file_type', 'Unknown') for r in results if r.get('file_type')))
    selected_file_type = st.sidebar.selectbox("File Type", file_types)
    
    # Apply filters
    filtered_results = results
    if selected_category != 'All':
        filtered_results = [r for r in filtered_results if r.get('source_category') == selected_category]
    
    if selected_file_type != 'All':
        filtered_results = [r for r in filtered_results if r.get('file_type') == selected_file_type]
    
    # Sort options
    sort_by = st.sidebar.selectbox("Sort By", ['Relevance', 'Source Trust', 'File Type'])
    if sort_by == 'Relevance':
        filtered_results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
    elif sort_by == 'Source Trust':
        filtered_results.sort(key=lambda x: (x.get('source_category') != 'unknown', x.get('relevance_score', 0)), reverse=True)
    else:  # File Type
        filtered_results.sort(key=lambda x: (x.get('file_type', ''), x.get('relevance_score', 0)), reverse=True)
    
    # Display results
    st.markdown(f"### Found {len(filtered_results)} datasets")
    
    for result in filtered_results:
        with st.expander(f"{result['title']} ({result.get('file_type', 'Unknown')})"):
            display_dataset_info(result)

def display_selected_datasets() -> None:
    """Display and manage selected datasets."""
    if not st.session_state.selected_results:
        st.info("No datasets selected yet. Use the search results to select datasets.")
        return
    
    st.markdown("### Selected Datasets")
    
    # Display selected datasets in a table
    selected_data = []
    for result in st.session_state.selected_results:
        selected_data.append({
            'Title': result['title'],
            'Source': result.get('source_name', 'Unknown'),
            'Category': result.get('source_category', 'Unknown'),
            'File Type': result.get('file_type', 'Unknown'),
            'URL': result['url']
        })
    
    df = pd.DataFrame(selected_data)
    st.dataframe(df)
    
    # Batch download options
    st.markdown("### Download Options")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Download All Selected"):
            for result in st.session_state.selected_results:
                download_dataset(result['url'])
    
    with col2:
        if st.button("Clear Selection"):
            st.session_state.selected_results = []
            st.experimental_rerun()

def download_dataset(url: str) -> None:
    """Download a dataset and update status."""
    try:
        # Get source information
        scraper = initialize_scraper()
        source_info = scraper._get_source_info(url)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9'
        }
        
        # Parse URL to handle query parameters
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        
        # Make a single request with stream=True
        with requests.get(url, headers=headers, stream=True, timeout=30) as response:
            # Check for authentication requirements
            if response.status_code == 403:
                st.session_state.download_status[url] = {
                    'status': 'restricted',
                    'error': 'Access restricted. This resource may require authentication.',
                    'source_info': source_info
                }
                return
                
            response.raise_for_status()
            
            # Get content type and size
            content_type = response.headers.get('content-type', '').lower()
            content_length = int(response.headers.get('content-length', 0))
            
            # Extract filename from various sources
            filename = None
            
            # Try to get filename from Content-Disposition header
            content_disposition = response.headers.get('content-disposition', '')
            if 'filename=' in content_disposition:
                filename_match = re.findall("filename=(.+)", content_disposition)
                if filename_match:
                    filename = filename_match[0].strip('"')
            
            # If no filename in header, try to get it from URL
            if not filename:
                # Get the last part of the path
                path_parts = parsed_url.path.strip('/').split('/')
                if path_parts:
                    filename = path_parts[-1]
                
                # If filename is empty or just a query parameter, use a default name
                if not filename or '=' in filename:
                    # Try to get a meaningful name from the URL path
                    if len(path_parts) > 1:
                        filename = path_parts[-2]  # Use the parent directory name
                    else:
                        filename = 'dataset'  # Default name
                    
                    # Add appropriate extension based on content type or query parameters
                    if 'format' in query_params:
                        format_param = query_params['format'][0].lower()
                        if format_param in ['csv', 'json', 'xlsx', 'xls', 'zip']:
                            filename += f'.{format_param}'
                    elif 'res_format' in query_params:
                        format_param = query_params['res_format'][0].lower()
                        if format_param in ['csv', 'json', 'xlsx', 'xls', 'zip']:
                            filename += f'.{format_param}'
                    else:
                        # Determine extension from content type
                        if 'csv' in content_type:
                            filename += '.csv'
                        elif 'json' in content_type:
                            filename += '.json'
                        elif 'excel' in content_type or 'spreadsheet' in content_type:
                            filename += '.xlsx'
                        elif 'zip' in content_type:
                            filename += '.zip'
                        else:
                            filename += '.csv'  # Default to CSV if we can't determine
            
            # Clean up filename
            filename = filename.replace('?', '').replace('&', '_').replace('=', '_')
            filename = re.sub(r'[<>:"/\\|?*]', '_', filename)  # Remove invalid characters
            
            # Create a progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Download the file with progress tracking
            downloaded_size = 0
            
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # Update progress if we know the total size
                        if content_length > 0:
                            progress = min(downloaded_size / content_length, 1.0)
                            progress_bar.progress(progress)
                            status_text.text(f"Downloading: {downloaded_size/1024/1024:.1f}MB / {content_length/1024/1024:.1f}MB")
            
            # Clear progress indicators
            progress_bar.empty()
            status_text.empty()
            
            # Verify the file was downloaded and has content
            if downloaded_size == 0:
                raise Exception("Downloaded file is empty")
            
            # Update download status
            st.session_state.download_status[url] = {
                'status': 'success',
                'filename': filename,
                'size': downloaded_size,
                'source_info': source_info
            }
            
            # Show success message with file location
            st.success(f"✅ Successfully downloaded to: {filename}")
        
    except requests.exceptions.HTTPError as e:
        st.session_state.download_status[url] = {
            'status': 'error',
            'error': f"HTTP error: {str(e)}",
            'source_info': source_info
        }
    except requests.exceptions.ConnectionError:
        st.session_state.download_status[url] = {
            'status': 'error',
            'error': "Connection error. Please check your internet connection.",
            'source_info': source_info
        }
    except requests.exceptions.Timeout:
        st.session_state.download_status[url] = {
            'status': 'error',
            'error': "Download timed out. Please try again.",
            'source_info': source_info
        }
    except Exception as e:
        st.session_state.download_status[url] = {
            'status': 'error',
            'error': f"Download failed: {str(e)}",
            'source_info': source_info
        }
        # Clean up empty file if it exists
        if 'filename' in locals() and os.path.exists(filename):
            os.remove(filename)

def display_download_status() -> None:
    """Display download status with source information."""
    if not st.session_state.download_status:
        return
        
    st.markdown("### Download Status")
    for url, status in st.session_state.download_status.items():
        if status['status'] == 'success':
            st.success(f"✅ Downloaded: {status['filename']} ({status['size']/1024/1024:.1f} MB)")
            if status.get('source_info'):
                st.info(f"Source: {status['source_info'].get('description', 'Unknown')}")
        elif status['status'] == 'restricted':
            st.error(f"🔒 {status['error']}")
            if status.get('source_info'):
                st.info(f"Source: {status['source_info'].get('description', 'Unknown')}")
        else:
            st.error(f"❌ Failed to download {url}: {status['error']}")

def main():
    st.set_page_config(
        page_title="Dataset Search Tool",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 Dataset Search Tool")
    st.markdown("""
    Search for datasets across trusted repositories including:
    - Government Data Portals (Data.gov, EU Open Data, etc.)
    - Academic Repositories (UCI ML, Harvard Dataverse, etc.)
    - International Organizations (World Bank, UN, IMF)
    - Specialized Collections (NOAA Climate, COVID-19, etc.)
    
    The tool focuses on finding structured datasets in common formats (CSV, JSON, Excel, etc.).
    """)
    
    # Initialize scraper
    scraper = initialize_scraper()
    
    # Search interface
    st.markdown("### Search Datasets")
    search_query = st.text_input(
        "Enter your search query",
        help="Try specific terms like 'climate data', 'economic indicators', or 'health statistics'"
    )
    
    if search_query:
        with st.spinner("Searching for datasets..."):
            results = scraper.search(search_query)
            st.session_state.search_results = results
        
        # Display results
        display_search_results(st.session_state.search_results)
        
        # Display selected datasets
        st.markdown("---")
        display_selected_datasets()
        
        # Display download status
        display_download_status()

if __name__ == "__main__":
    main() 