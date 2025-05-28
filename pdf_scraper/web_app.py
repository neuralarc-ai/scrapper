import streamlit as st
import pandas as pd
from core.scrapers.general import GeneralWebScraper
import json
from datetime import datetime
import os
from dotenv import load_dotenv
import requests # Import requests for downloading files
import zipfile # Import zipfile for creating archives
import io # Import io for handling in-memory files

def main():
    # Load environment variables from .env file
    load_dotenv()

    st.title("Universal PDF Search & Scraper")
    st.write("Search and extract PDF documents from the web based on any topic or requirement. Enter your query below to find relevant PDFs.")
    
    # Get API Key and CSE ID from environment variables
    api_key = os.getenv("GOOGLE_API_KEY")
    cse_id = os.getenv("GOOGLE_CSE_ID")

    if not api_key or not cse_id:
        st.error("Google API Key or Custom Search Engine ID not found.")
        st.info("Please create a .env file in the project root with GOOGLE_API_KEY and GOOGLE_CSE_ID.")
        st.info("You can get them from the Google Cloud Console and Google Custom Search Engine website.")
        return

    # Initialize general-purpose scraper with credentials
    # The scraper is configured to specifically search for PDF files.
    scraper = GeneralWebScraper(api_key=api_key, cse_id=cse_id)
    
    # Search query
    query = st.text_input("Enter your search query")
    
    # Number of results
    # Google Custom Search API allows up to 100 results per query
    max_results = st.slider("Maximum number of results", 5, 100, 10)
    
    # Store results in session state to persist after rerun
    if 'search_results' not in st.session_state:
        st.session_state.search_results = []

    if st.button("Search"):
        if query:
            with st.spinner("Searching the web for PDFs..."):
                try:
                    results = scraper.search(query, max_results=max_results)
                    st.session_state.search_results = results # Save results to session state
                    
                    if results:
                        st.success(f"Found {len(results)} PDF results!")
                    else:
                        st.warning("No PDF results found. Try a different query.")
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
        else:
            st.warning("Please enter a search query.")
            st.session_state.search_results = [] # Clear results if query is empty

    # Display results if available in session state
    if st.session_state.search_results:
        results = st.session_state.search_results
        # Convert results to DataFrame for better display
        df = pd.DataFrame(results)
        
        # Display results
        st.dataframe(df)
        
        # Download options
        st.subheader("Download Options")
        
        # JSON download
        json_str = json.dumps(results, indent=2)
        st.download_button(
            label="Download Results as JSON",
            data=json_str,
            file_name=f"pdf_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
        
        # CSV download
        csv = df.to_csv(index=False).encode('utf-8') # Encode CSV to bytes
        st.download_button(
            label="Download Results as CSV",
            data=csv,
            file_name=f"pdf_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

        # Function to download and zip files
        @st.cache_data # Cache the output of this function
        def download_and_zip_pdfs(pdf_urls):
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for i, url in enumerate(pdf_urls):
                    try:
                        response = requests.get(url, stream=True)
                        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
                        
                        # Extract filename from URL or use a generic name
                        filename = url.split('/')[-1] or f"document_{i+1}.pdf"
                        if '.pdf' not in filename.lower():
                            filename = f"document_{i+1}.pdf"
                            
                        zip_file.writestr(filename, response.content)
                        # Use response.content for smaller files or iterate with chunks for large files
                        # For potentially large files, consider:
                        # with response as r:
                        #     zip_file.writestr(filename, r.iter_content(chunk_size=8192))
                            
                    except Exception as e:
                        print(f"Error downloading {url}: {e}")
                        # Optionally add a placeholder file in the zip indicating the failure
                        zip_file.writestr(f"error_downloading_{i+1}.txt", f"Failed to download {url}: {e}")
                        
            return zip_buffer.getvalue() # Return bytes

        # Download All PDFs button
        pdf_urls = [result.get('url') for result in results if result.get('url')] # Get list of valid URLs
        if pdf_urls:
            zip_data = download_and_zip_pdfs(pdf_urls)
            st.download_button(
                label="Download All PDFs",
                data=zip_data,
                file_name=f"all_pdfs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                mime="application/zip"
            )
        else:
            st.info("No valid PDF URLs found in the results to download.")

        
        # Detailed view (Note: Summarization might not work for all PDF links)
        st.subheader("Detailed View")
        st.info("Note: Summarization is primarily for HTML pages and may not work for all PDF links.")
        for idx, result in enumerate(results, 1):
            with st.expander(f"{idx}. {result['title']}"):
                st.write("**Snippet:**", result.get('snippet', 'N/A'))
                st.write("**URL:**", result.get('url', 'N/A'))
                # Optionally add a download link for the PDF itself
                if result.get('url'):
                     st.markdown(f"[Open/Download PDF]({result.get('url')})", unsafe_allow_html=True)
                else:
                    st.write("No URL available for this result.")


    else:
        # Display initial message or no results message if search hasn't run or found nothing
        if 'search_results' in st.session_state and st.session_state.search_results == []:
             st.info("Enter a query and click Search to find PDF documents.")
        

if __name__ == "__main__":
    main() 