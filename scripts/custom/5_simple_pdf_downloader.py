import pandas as pd
import requests
import time
import os
from datetime import datetime
import urllib.parse
import re
from bs4 import BeautifulSoup
import random

def get_simple_session():
    """Create a simple requests session with headers"""
    session = requests.Session()

    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ]

    session.headers.update({
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    })

    return session

def search_arxiv_simple(title):
    """Simple arXiv search"""
    try:
        session = get_simple_session()

        # Clean title and search
        clean_title = re.sub(r'[^\w\s]', ' ', title).strip()
        search_terms = ' '.join(clean_title.split()[:6])  # First 6 words

        # Try arXiv API first
        arxiv_url = "http://export.arxiv.org/api/query"
        params = {
            'search_query': f'all:"{search_terms}"',
            'start': 0,
            'max_results': 5
        }

        print(f"   🔍 Searching arXiv...")
        response = session.get(arxiv_url, params=params, timeout=15)

        if response.status_code == 200:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.content)

            for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
                arxiv_title = entry.find('{http://www.w3.org/2005/Atom}title').text.strip()

                # Check if titles have common words
                title_words = set(w.lower() for w in title.split() if len(w) > 3)
                arxiv_words = set(w.lower() for w in arxiv_title.split() if len(w) > 3)
                common_words = title_words.intersection(arxiv_words)

                if len(common_words) >= 2:  # At least 2 common words
                    for link in entry.findall('{http://www.w3.org/2005/Atom}link'):
                        if link.get('type') == 'application/pdf':
                            pdf_url = link.get('href')
                            return {
                                'found': True,
                                'source': 'arXiv',
                                'title': arxiv_title,
                                'pdf_url': pdf_url
                            }

        return {'found': False, 'source': 'arXiv'}

    except Exception as e:
        print(f"   ❌ arXiv error: {str(e)}")
        return {'found': False, 'source': 'arXiv'}

def search_semantic_scholar_simple(title):
    """Simple Semantic Scholar search with rate limiting"""
    try:
        search_url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            'query': title,
            'limit': 3,
            'fields': 'paperId,title,openAccessPdf'
        }

        print(f"   🔍 Searching Semantic Scholar...")
        time.sleep(random.uniform(4, 7))  # Random delay to avoid rate limiting

        response = requests.get(search_url, params=params, timeout=20)

        if response.status_code == 429:
            print(f"   ⏳ Rate limited, waiting...")
            time.sleep(45)
            response = requests.get(search_url, params=params, timeout=20)

        if response.status_code == 200:
            data = response.json()

            if 'data' in data and len(data['data']) > 0:
                for paper in data['data']:
                    paper_title = paper.get('title', '')

                    # Check title similarity
                    if (title.lower() in paper_title.lower() or
                        paper_title.lower() in title.lower() or
                        len(set(title.lower().split()).intersection(set(paper_title.lower().split()))) >= 3):

                        # Check for PDF
                        pdf_url = ""
                        if paper.get('openAccessPdf') and paper['openAccessPdf'].get('url'):
                            pdf_url = paper['openAccessPdf']['url']

                        return {
                            'found': True,
                            'semantic_title': paper_title,
                            'pdf_url': pdf_url,
                            'source': 'Semantic Scholar'
                        }

        return {'found': False, 'source': 'Semantic Scholar'}

    except Exception as e:
        print(f"   ❌ Semantic Scholar error: {str(e)}")
        return {'found': False, 'source': 'Semantic Scholar'}

def download_and_validate_pdf(pdf_url, pdf_path, source_name):
    """Download and validate PDF"""
    try:
        session = get_simple_session()

        # Add appropriate headers based on source
        headers = {}
        if 'arxiv.org' in pdf_url:
            headers['Referer'] = 'https://arxiv.org/'

        print(f"   📥 Downloading from {source_name}: {pdf_url}")
        response = session.get(pdf_url, timeout=30, stream=True, headers=headers)

        if response.status_code == 403:
            print(f"   ❌ Access forbidden (403)")
            return False

        response.raise_for_status()

        # Check content type
        content_type = response.headers.get('content-type', '').lower()
        if 'pdf' not in content_type and not pdf_url.endswith('.pdf'):
            print(f"   ❌ Not a PDF: {content_type}")
            return False

        # Download file
        with open(pdf_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # Validate file
        file_size = os.path.getsize(pdf_path)
        if file_size < 1024:  # Less than 1KB
            os.remove(pdf_path)
            print(f"   ❌ File too small: {file_size} bytes")
            return False

        # Check PDF header
        with open(pdf_path, 'rb') as f:
            header = f.read(4)
            if not header.startswith(b'%PDF'):
                os.remove(pdf_path)
                print(f"   ❌ Invalid PDF header")
                return False

        print(f"   ✅ Downloaded successfully: {file_size/1024:.1f}KB")
        return True

    except Exception as e:
        print(f"   ❌ Download failed: {str(e)}")
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        return False

def find_and_download_pdf(title, authors=""):
    """Main function to find and download PDF"""
    # Create safe filename
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
    safe_title = safe_title[:80]  # Shorter filename
    pdf_filename = f"{safe_title}.pdf"

    # PDF directory
    pdf_dir = "/Users/reddy/2025/ResearchHelper/results/pdf"
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_path = os.path.join(pdf_dir, pdf_filename)

    # Skip if already exists
    if os.path.exists(pdf_path):
        print(f"   ✅ PDF already exists")
        return {
            'pdf_downloaded': True,
            'pdf_filename': pdf_filename,
            'pdf_source': 'Already downloaded',
            'sources_tried': ['Local file']
        }

    sources_tried = []

    # Try Semantic Scholar first
    result = search_semantic_scholar_simple(title)
    sources_tried.append('Semantic Scholar')

    if result.get('found') and result.get('pdf_url'):
        if download_and_validate_pdf(result['pdf_url'], pdf_path, 'Semantic Scholar'):
            return {
                'pdf_downloaded': True,
                'pdf_filename': pdf_filename,
                'pdf_source': 'Semantic Scholar',
                'pdf_url': result['pdf_url'],
                'sources_tried': sources_tried
            }

    # Try arXiv
    time.sleep(2)
    result = search_arxiv_simple(title)
    sources_tried.append('arXiv')

    if result.get('found') and result.get('pdf_url'):
        if download_and_validate_pdf(result['pdf_url'], pdf_path, 'arXiv'):
            return {
                'pdf_downloaded': True,
                'pdf_filename': pdf_filename,
                'pdf_source': 'arXiv',
                'pdf_url': result['pdf_url'],
                'sources_tried': sources_tried
            }

    return {
        'pdf_downloaded': False,
        'pdf_filename': "",
        'pdf_source': "",
        'pdf_url': "",
        'sources_tried': sources_tried
    }

def main():
    # Read the previous results
    csv_path = "/Users/reddy/2025/ResearchHelper/results/papers_pdf_download_20250810_160202.csv"

    try:
        df = pd.read_csv(csv_path)

        # Filter papers without PDFs
        failed_papers = df[df['pdf_downloaded'] == False].copy()

        print(f"Found {len(failed_papers)} papers without PDFs")
        print("Starting simple PDF search...")
        print("=" * 80)

        results = []
        successful_downloads = 0

        # Process in smaller batches to avoid overwhelming APIs
        batch_size = 20
        total_batches = (len(failed_papers) + batch_size - 1) // batch_size

        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(failed_papers))
            batch_papers = failed_papers.iloc[start_idx:end_idx]

            print(f"\n📦 Processing batch {batch_num + 1}/{total_batches} ({len(batch_papers)} papers)")

            for idx, (_, row) in enumerate(batch_papers.iterrows()):
                title = row['original_title']
                original_id = row['original_id']
                authors = row.get('authors', '') if pd.notna(row.get('authors')) else ""

                print(f"\n[{start_idx + idx + 1}/{len(failed_papers)}] {title[:60]}...")

                # Search and download
                download_result = find_and_download_pdf(title, authors)

                if download_result['pdf_downloaded']:
                    successful_downloads += 1

                result = {
                    'original_id': original_id,
                    'original_title': title,
                    'pdf_downloaded': download_result['pdf_downloaded'],
                    'pdf_filename': download_result['pdf_filename'],
                    'pdf_source': download_result.get('pdf_source', ''),
                    'pdf_url': download_result.get('pdf_url', ''),
                    'sources_tried': ', '.join(download_result.get('sources_tried', []))
                }

                results.append(result)

                # Rate limiting between papers
                time.sleep(3)

            # Longer break between batches
            if batch_num < total_batches - 1:
                print(f"\n⏸️  Break between batches (60 seconds)...")
                time.sleep(60)

        # Save results
        results_df = pd.DataFrame(results)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"/Users/reddy/2025/ResearchHelper/results/simple_pdf_download_{timestamp}.csv"
        results_df.to_csv(output_path, index=False)

        print("\n" + "=" * 80)
        print("SIMPLE PDF DOWNLOAD SUMMARY:")
        print(f"Papers processed: {len(failed_papers)}")
        print(f"PDFs downloaded: {successful_downloads}")
        print(f"Success rate: {(successful_downloads/len(failed_papers)*100):.1f}%")
        print(f"Results saved to: {output_path}")
        print("=" * 80)

        # Show successful downloads
        successful_results = [r for r in results if r['pdf_downloaded']]
        if successful_results:
            print(f"\n✅ Successfully downloaded {len(successful_results)} PDFs:")
            for i, result in enumerate(successful_results[:10], 1):  # Show first 10
                print(f"{i}. {result['original_title'][:50]}... ({result['pdf_source']})")
            if len(successful_results) > 10:
                print(f"... and {len(successful_results) - 10} more")

    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main()
