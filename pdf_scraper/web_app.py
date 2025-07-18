import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
import time
import requests
from typing import Dict, Any, List
import json
from urllib.parse import urlparse, parse_qs
import re
from kaggle.api.kaggle_api_extended import KaggleApi
from pathlib import Path
import platform

# Load environment variables
load_dotenv()

# Set Kaggle credentials from environment variables
os.environ['KAGGLE_USERNAME'] = os.getenv('KAGGLE_USERNAME', 'sahilempire')
os.environ['KAGGLE_KEY'] = os.getenv('KAGGLE_KEY', '0875b95075f73482ec91b60d5ba8736a')

# Initialize session state
if 'search_results' not in st.session_state:
    st.session_state.search_results = []
if 'selected_results' not in st.session_state:
    st.session_state.selected_results = []
if 'download_status' not in st.session_state:
    st.session_state.download_status = {}
if 'kaggle_api' not in st.session_state:
    st.session_state.kaggle_api = None

def initialize_kaggle_api() -> KaggleApi:
    """Initialize the Kaggle API client."""
    if st.session_state.kaggle_api is None:
        try:
            api = KaggleApi()
            api.authenticate()
            st.session_state.kaggle_api = api
        except Exception as e:
            st.error(f"Failed to authenticate with Kaggle: {str(e)}")
            st.stop()
    
    return st.session_state.kaggle_api

def search_kaggle_datasets(query: str) -> List[Dict[str, Any]]:
    """Search for datasets on Kaggle using the Kaggle API."""
    api = initialize_kaggle_api()
    datasets = api.dataset_list(search=query)
    results = []
    for dataset in datasets:
        results.append({
            'title': dataset.title,
            'url': f"https://www.kaggle.com/datasets/{dataset.ref}",
            'snippet': dataset.description,
            'file_type': 'csv',  # Default assumption
            'relevance_score': 1.0  # Placeholder score
        })
    return results

def display_dataset_info(result: Dict[str, Any]) -> None:
    """Display detailed information about a dataset."""
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown(f"### [{result['title']}]({result['url']})")
        st.markdown(result['snippet'])
        st.info(f"📊 File Type: {result['file_type'].upper()}")
    
    with col2:
        score = result.get('relevance_score', 0)
        st.metric("Relevance Score", f"{score:.1f}")
        
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
    
    st.markdown(f"### Found {len(results)} datasets")
    
    for result in results:
        with st.expander(f"{result['title']} ({result.get('file_type', 'Unknown')})"):
            display_dataset_info(result)

def display_selected_datasets() -> None:
    """Display and manage selected datasets."""
    if not st.session_state.selected_results:
        st.info("No datasets selected yet. Use the search results to select datasets.")
        return
    
    st.markdown("### Selected Datasets")
    
    selected_data = []
    for result in st.session_state.selected_results:
        selected_data.append({
            'Title': result['title'],
            'URL': result['url']
        })
    
    df = pd.DataFrame(selected_data)
    st.dataframe(df)
    
    st.markdown("### Download Options")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Download All Selected"):
            for result in st.session_state.selected_results:
                download_dataset(result['url'])
    
    with col2:
        if st.button("Clear Selection"):
            st.session_state.selected_results = []
            st.rerun()

def get_downloads_folder() -> str:
    """Get the Downloads folder path for the current operating system and user."""
    home = Path.home()
    system = platform.system()
    downloads = home / "Downloads"

    if downloads.exists():
        return str(downloads)
    else:
        # Fallback: create the Downloads folder if it doesn't exist
        try:
            downloads.mkdir(parents=True, exist_ok=True)
            return str(downloads)
        except Exception as e:
            st.error(f"Could not create or find Downloads folder at: {downloads}. Error: {e}")
            return None

def download_dataset(url: str) -> None:
    """Download a dataset from Kaggle using the Kaggle API."""
    try:
        api = initialize_kaggle_api()
        # Extract dataset reference from URL (username/dataset-name)
        dataset_ref = '/'.join(url.split('/')[-2:])
        
        # Get Downloads folder path
        downloads_dir = get_downloads_folder()
        if not downloads_dir:
            return
        
        # Create a subdirectory for this specific dataset in Downloads
        dataset_name = dataset_ref.split('/')[-1]
        dataset_dir = os.path.join(downloads_dir, dataset_name)
        
        # Remove existing directory if it exists
        if os.path.exists(dataset_dir):
            import shutil
            shutil.rmtree(dataset_dir)
        
        # Create fresh directory
        os.makedirs(dataset_dir, exist_ok=True)
        
        # Download the dataset directly to Downloads
        with st.spinner(f"Downloading {dataset_name} to Downloads folder..."):
            api.dataset_download_files(
                dataset_ref,
                path=dataset_dir,
                unzip=True,
                force=True  # Force download even if files exist
            )
        
        # Get the list of downloaded files
        downloaded_files = os.listdir(dataset_dir)
        
        if not downloaded_files:
            raise Exception("No files were downloaded")
        
        st.session_state.download_status[url] = {
            'status': 'success',
            'filename': dataset_name,
            'path': dataset_dir,
            'files': downloaded_files
        }
        
        # Show success message with file locations
        st.success(f"✅ Successfully downloaded dataset: {dataset_name}")
        st.info(f"📁 Location: {dataset_dir}")
        st.info("📄 Files downloaded:")
        for file in downloaded_files:
            file_path = os.path.join(dataset_dir, file)
            file_size = os.path.getsize(file_path) / (1024 * 1024)  # Size in MB
            st.write(f"- {file} ({file_size:.1f} MB)")
            
    except Exception as e:
        st.session_state.download_status[url] = {
            'status': 'error',
            'error': f"Download failed: {str(e)}"
        }
        # Clean up if download failed
        if 'dataset_dir' in locals() and os.path.exists(dataset_dir):
            import shutil
            shutil.rmtree(dataset_dir)

def display_download_status() -> None:
    """Display download status."""
    if not st.session_state.download_status:
        return
        
    st.markdown("### Download Status")
    for url, status in st.session_state.download_status.items():
        if status['status'] == 'success':
            st.success(f"✅ Downloaded: {status['filename']}")
            st.info(f"📁 Location: {status['path']}")
            if 'files' in status:
                st.write("📄 Files:")
                for file in status['files']:
                    st.write(f"- {file}")
        else:
            st.error(f"❌ Failed to download {url}: {status['error']}")

def main():
    st.set_page_config(
        page_title="Kaggle Dataset Search Tool",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 Kaggle Dataset Search Tool")
    st.markdown("""
    Search for datasets on Kaggle. Enter your query below to find matching datasets.
    """)
    
    # Search interface
    st.markdown("### Search Datasets")
    search_query = st.text_input(
        "Enter your search query",
        help="Try specific terms like 'climate data', 'economic indicators', or 'health statistics'"
    )
    
    if search_query:
        with st.spinner("Searching for datasets..."):
            results = search_kaggle_datasets(search_query)
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