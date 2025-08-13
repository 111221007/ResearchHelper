import pandas as pd
import requests
import time
import json
import os
from datetime import datetime
import urllib.parse
from pathlib import Path
import re
from bs4 import BeautifulSoup
import random
from urllib.parse import urljoin, urlparse
import ssl
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_robust_session():
    """
    Create a robust requests session with retry logic and headers
    """
    session = requests.Session()

    # Retry strategy (fixed for newer urllib3)
    retry_strategy = Retry(
        total=3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"],  # Fixed deprecated parameter
        backoff_factor=1
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Random user agents to avoid detection
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0'
    ]

    session.headers.update({
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0'
    })

    return session

def search_arxiv_for_pdf(title, authors=""):
    """
    Search arXiv for PDF using title and authors with web scraping fallback
    """
    try:
        session = get_robust_session()

        # Method 1: arXiv API
        clean_title = re.sub(r'[^\w\s]', ' ', title).strip()
        clean_title = ' '.join(clean_title.split()[:8])  # First 8 words only

        arxiv_url = "http://export.arxiv.org/api/query"
        params = {
            'search_query': f'all:"{clean_title}"',
            'start': 0,
            'max_results': 5
        }

        print(f"   🔍 Searching arXiv API...")
        response = session.get(arxiv_url, params=params, timeout=15)

        if response.status_code == 200:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.content)

            for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
                arxiv_title = entry.find('{http://www.w3.org/2005/Atom}title').text.strip()

                # Fuzzy title matching
                title_words = set(w.lower() for w in title.split() if len(w) > 3)
                arxiv_words = set(w.lower() for w in arxiv_title.split() if len(w) > 3)
                common_words = title_words.intersection(arxiv_words)

                if len(common_words) >= min(2, len(title_words) * 0.4):
                    for link in entry.findall('{http://www.w3.org/2005/Atom}link'):
                        if link.get('type') == 'application/pdf':
                            pdf_url = link.get('href')
                            return {
                                'found': True,
                                'source': 'arXiv-API',
                                'title': arxiv_title,
                                'pdf_url': pdf_url
                            }

        # Method 2: Direct arXiv search with simpler query
        search_terms = '+'.join(title.split()[:4])  # First 4 words
        arxiv_search_url = f"https://arxiv.org/search/?query={search_terms}&searchtype=all"

        print(f"   🔍 Searching arXiv web...")
        time.sleep(1)
        response = session.get(arxiv_search_url, timeout=15)

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            for result in soup.find_all('li', class_='arxiv-result'):
                title_elem = result.find('p', class_='title')
                if title_elem:
                    arxiv_title = title_elem.get_text().strip()

                    # Check title similarity (more lenient)
                    if any(word.lower() in arxiv_title.lower() for word in title.split()[:3] if len(word) > 3):
                        # Look for PDF link
                        links = result.find_all('a')
                        for link in links:
                            href = link.get('href', '')
                            if '/pdf/' in href:
                                pdf_url = urljoin('https://arxiv.org', href)
                                return {
                                    'found': True,
                                    'source': 'arXiv-Web',
                                    'title': arxiv_title,
                                    'pdf_url': pdf_url
                                }

        return {'found': False, 'source': 'arXiv'}

    except Exception as e:
        print(f"   ❌ arXiv search error: {str(e)}")
        return {'found': False, 'source': 'arXiv', 'error': str(e)}

def search_semantic_scholar_with_fallback(title):
    """
    Enhanced Semantic Scholar search with better error handling
    """
    try:
        session = get_robust_session()

        search_url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            'query': title,
            'limit': 3,
            'fields': 'paperId,title,abstract,year,authors,venue,url,openAccessPdf,isOpenAccess,externalIds'
        }

        print(f"   🔍 Searching Semantic Scholar...")
        time.sleep(random.uniform(3, 6))  # Random delay

        response = session.get(search_url, params=params, timeout=20)

        if response.status_code == 429:
            print(f"   ⏳ Rate limited, waiting...")
            time.sleep(30)
            response = session.get(search_url, params=params, timeout=20)

        if response.status_code == 200:
            data = response.json()

            if 'data' in data and len(data['data']) > 0:
                for paper in data['data']:
                    paper_title = paper.get('title', '')

                    if title.lower() in paper_title.lower() or paper_title.lower() in title.lower():
                        # Check for PDF
                        pdf_url = ""
                        if paper.get('openAccessPdf') and paper['openAccessPdf'].get('url'):
                            pdf_url = paper['openAccessPdf']['url']

                        return {
                            'found': True,
                            'semantic_title': paper_title,
                            'pdf_url': pdf_url,
                            'year': paper.get('year', ''),
                            'venue': paper.get('venue', ''),
                            'paper_id': paper.get('paperId', ''),
                            'url': paper.get('url', '')
                        }

        return {'found': False}

    except Exception as e:
        print(f"   ❌ Semantic Scholar failed: {str(e)}")
        return {'found': False, 'error': str(e)}

def search_alternative_sources(title, authors=""):
    """
    Search alternative academic repositories and preprint servers
    """
    try:
        session = get_robust_session()

        # Try bioRxiv for biological/computational papers
        if any(keyword in title.lower() for keyword in ['bio', 'protein', 'gene', 'cell', 'molecular']):
            print(f"   🔍 Searching bioRxiv...")
            biorxiv_url = f"https://www.biorxiv.org/search/{urllib.parse.quote(title[:50])}"
            try:
                response = session.get(biorxiv_url, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    for link in soup.find_all('a', href=re.compile(r'\.pdf')):
                        pdf_url = urljoin('https://www.biorxiv.org', link.get('href'))
                        return {
                            'found': True,
                            'source': 'bioRxiv',
                            'pdf_url': pdf_url
                        }
            except:
                pass

        # Try IEEE Xplore for engineering papers
        if any(keyword in title.lower() for keyword in ['computing', 'algorithm', 'network', 'system', 'software']):
            print(f"   🔍 Searching IEEE...")
            ieee_query = '+'.join(title.split()[:5])
            ieee_url = f"https://ieeexplore.ieee.org/search/searchresult.jsp?newsearch=true&queryText={ieee_query}"
            try:
                response = session.get(ieee_url, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    for link in soup.find_all('a', href=re.compile(r'/document/\d+')):
                        # IEEE papers often require subscription, but we can try
                        doc_url = urljoin('https://ieeexplore.ieee.org', link.get('href'))
                        return {
                            'found': True,
                            'source': 'IEEE Xplore',
                            'pdf_url': doc_url
                        }
            except:
                pass

        # Try ResearchGate
        print(f"   🔍 Searching ResearchGate...")
        rg_query = title.replace(' ', '%20')
        rg_url = f"https://www.researchgate.net/search/publication?q={rg_query}"
        try:
            time.sleep(2)
            response = session.get(rg_url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                # Look for publication links
                for link in soup.find_all('a', href=re.compile(r'/publication/\d+')):
                    pub_url = urljoin('https://www.researchgate.net', link.get('href'))
                    return {
                        'found': True,
                        'source': 'ResearchGate',
                        'pdf_url': pub_url  # Not direct PDF but publication page
                    }
        except:
            pass

        return {'found': False, 'source': 'Alternative Sources'}

    except Exception as e:
        print(f"   ❌ Alternative sources error: {str(e)}")
        return {'found': False, 'source': 'Alternative Sources', 'error': str(e)}

def download_pdf_with_validation(pdf_url, pdf_path, source_name):
    """
    Download and validate PDF file
    """
    try:
        session = get_robust_session()

        print(f"   📥 Downloading from {source_name}: {pdf_url}")

        # Special handling for different sources
        headers = {}
        if 'arxiv.org' in pdf_url:
            headers.update({
                'Referer': 'https://arxiv.org/',
            })
        elif 'researchgate.net' in pdf_url:
            headers.update({
                'Referer': 'https://www.researchgate.net/',
            })

        response = session.get(pdf_url, timeout=30, stream=True, headers=headers)
        response.raise_for_status()

        # Check if response is actually a PDF
        content_type = response.headers.get('content-type', '').lower()

        if 'pdf' in content_type or pdf_url.endswith('.pdf'):
            # Check file size (avoid downloading huge files or tiny error pages)
            content_length = response.headers.get('content-length')
            if content_length:
                size_mb = int(content_length) / (1024 * 1024)
                if size_mb > 100:  # Skip files larger than 100MB
                    print(f"   ❌ File too large: {size_mb:.1f}MB")
                    return False
                elif size_mb < 0.01:  # Skip files smaller than 10KB
                    print(f"   ❌ File too small: {size_mb*1024:.1f}KB")
                    return False

            with open(pdf_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # Validate downloaded file
            file_size = os.path.getsize(pdf_path)
            if file_size < 1024:  # Less than 1KB is likely an error page
                os.remove(pdf_path)
                print(f"   ❌ Downloaded file too small: {file_size} bytes")
                return False

            # Check if file starts with PDF header
            with open(pdf_path, 'rb') as f:
                header = f.read(4)
                if not header.startswith(b'%PDF'):
                    os.remove(pdf_path)
                    print(f"   ❌ Not a valid PDF file")
                    return False

            print(f"   ✅ PDF downloaded successfully: {file_size/1024:.1f}KB")
            return True
        else:
            print(f"   ❌ Not a PDF: {content_type}")
            return False

    except Exception as e:
        print(f"   ❌ Download failed: {str(e)}")
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        return False

def comprehensive_pdf_search_and_download(title, authors="", doi="", venue=""):
    """
    Comprehensive PDF search using all available sources with better error handling
    """
    pdf_downloaded = False
    pdf_filename = ""
    pdf_sources_tried = []

    # Create safe filename
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
    safe_title = safe_title[:100]
    pdf_filename = f"{safe_title}.pdf"

    # Create PDF directory
    pdf_dir = "/Users/reddy/2025/ResearchHelper/results/pdf"
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_path = os.path.join(pdf_dir, pdf_filename)

    # Skip if already downloaded
    if os.path.exists(pdf_path):
        print(f"   ✅ PDF already exists: {pdf_filename}")
        return {
            'pdf_downloaded': True,
            'pdf_filename': pdf_filename,
            'pdf_source': 'Already downloaded',
            'sources_tried': ['Local file']
        }

    # Expanded list of sources
    sources = [
        ('Semantic Scholar', lambda: retry_failed_semantic_scholar(title)),
        ('arXiv', lambda: search_arxiv_for_pdf(title, authors)),
        ('Google Scholar', lambda: search_google_scholar_pdf(title, authors)),
        ('ResearchGate', lambda: search_researchgate_pdf(title, authors)),
        ('DOI/Sci-Hub', lambda: search_doi_and_scihub(title, doi)),
        ('IEEE/ACM Direct', lambda: search_ieee_acm_direct(title, authors)),
        ('Alternative Sources', lambda: search_alternative_sources(title, authors)),
    ]

    for source_name, search_func in sources:
        try:
            print(f"   🔍 Trying {source_name}...")
            result = search_func()
            pdf_sources_tried.append(source_name)

            if result.get('found') and result.get('pdf_url'):
                pdf_url = result['pdf_url']

                try:
                    # Download with validation
                    if download_pdf_with_validation(pdf_url, pdf_path, source_name):
                        pdf_downloaded = True
                        print(f"   ✅ PDF downloaded from {source_name}: {pdf_filename}")

                        return {
                            'pdf_downloaded': True,
                            'pdf_filename': pdf_filename,
                            'pdf_url': pdf_url,
                            'pdf_source': source_name,
                            'sources_tried': pdf_sources_tried
                        }
                except Exception as download_error:
                    print(f"   ❌ Download failed from {source_name}: {str(download_error)}")
                    continue

            # Rate limiting between sources
            time.sleep(1)

        except Exception as source_error:
            print(f"   ❌ {source_name} search failed: {str(source_error)}")
            continue

    return {
        'pdf_downloaded': False,
        'pdf_filename': "",
        'pdf_url': "",
        'pdf_source': "",
        'sources_tried': pdf_sources_tried
    }

def retry_failed_semantic_scholar(title):
    """
    Retry Semantic Scholar with longer delays and error handling
    """
    try:
        search_url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            'query': title,
            'limit': 3,
            'fields': 'paperId,title,abstract,year,authors,venue,url,openAccessPdf,isOpenAccess,externalIds'
        }

        print(f"   🔍 Retrying Semantic Scholar: {title[:50]}...")

        # Add longer delay for rate limiting
        time.sleep(5)

        response = requests.get(search_url, params=params, timeout=20)

        if response.status_code == 429:
            print(f"   ⏳ Rate limited, waiting 30 seconds...")
            time.sleep(30)
            response = requests.get(search_url, params=params, timeout=20)

        response.raise_for_status()
        data = response.json()

        if 'data' in data and len(data['data']) > 0:
            for paper in data['data']:
                paper_title = paper.get('title', '')

                if title.lower() in paper_title.lower() or paper_title.lower() in title.lower():
                    # Extract DOI if available
                    doi = ""
                    external_ids = paper.get('externalIds', {})
                    if external_ids and external_ids.get('DOI'):
                        doi = external_ids['DOI']

                    # Get authors
                    authors = []
                    if paper.get('authors'):
                        authors = [author.get('name', '') for author in paper['authors']]
                    authors_str = ', '.join(authors)

                    # Check for PDF
                    pdf_url = ""
                    if paper.get('openAccessPdf') and paper['openAccessPdf'].get('url'):
                        pdf_url = paper['openAccessPdf']['url']

                    return {
                        'found': True,
                        'semantic_title': paper_title,
                        'authors': authors_str,
                        'doi': doi,
                        'pdf_url': pdf_url,
                        'year': paper.get('year', ''),
                        'venue': paper.get('venue', ''),
                        'paper_id': paper.get('paperId', ''),
                        'url': paper.get('url', '')
                    }

        return {'found': False}

    except Exception as e:
        print(f"   ❌ Semantic Scholar retry failed: {str(e)}")
        return {'found': False, 'error': str(e)}

def enhanced_pdf_search_and_download(title, authors="", doi="", venue=""):
    """
    Enhanced PDF search using all available sources with web scraping
    """
    return comprehensive_pdf_search_and_download(title, authors, doi, venue)

def search_google_scholar_pdf(title, authors=""):
    """
    Search Google Scholar for PDF (limited due to anti-bot measures)
    """
    try:
        # Google Scholar has strong anti-bot measures, so this is a basic implementation
        session = get_robust_session()

        # Simple Google Scholar search
        query = title.replace(' ', '+')
        scholar_url = f"https://scholar.google.com/scholar?q={query}"

        print(f"   🔍 Searching Google Scholar...")
        time.sleep(2)  # Be respectful

        response = session.get(scholar_url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for PDF links
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                if href and ('.pdf' in href or 'pdf' in href.lower()):
                    return {
                        'found': True,
                        'source': 'Google Scholar',
                        'pdf_url': href
                    }

        return {'found': False, 'source': 'Google Scholar'}

    except Exception as e:
        print(f"   ❌ Google Scholar search error: {str(e)}")
        return {'found': False, 'source': 'Google Scholar', 'error': str(e)}

def search_researchgate_pdf(title, authors=""):
    """
    Search ResearchGate for PDFs
    """
    try:
        session = get_robust_session()

        query = title.replace(' ', '%20')
        rg_url = f"https://www.researchgate.net/search/publication?q={query}"

        print(f"   🔍 Searching ResearchGate...")
        time.sleep(2)

        response = session.get(rg_url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for publication links that might have PDFs
            for link in soup.find_all('a', href=re.compile(r'/publication/\d+')):
                pub_url = urljoin('https://www.researchgate.net', link.get('href'))
                # Note: ResearchGate PDFs usually require login, but we can try
                return {
                    'found': True,
                    'source': 'ResearchGate',
                    'pdf_url': pub_url
                }

        return {'found': False, 'source': 'ResearchGate'}

    except Exception as e:
        print(f"   ❌ ResearchGate search error: {str(e)}")
        return {'found': False, 'source': 'ResearchGate', 'error': str(e)}

def search_doi_and_scihub(title, doi=""):
    """
    Search using DOI and try Sci-Hub as a last resort
    """
    try:
        if not doi:
            return {'found': False, 'source': 'DOI/Sci-Hub', 'error': 'No DOI provided'}

        session = get_robust_session()

        # Try the official DOI resolver first
        doi_url = f"https://doi.org/{doi}"
        print(f"   🔍 Trying DOI resolver...")

        response = session.get(doi_url, timeout=10, allow_redirects=True)
        if response.status_code == 200:
            # Check if we got redirected to a PDF
            final_url = response.url
            if '.pdf' in final_url.lower() or 'pdf' in response.headers.get('content-type', '').lower():
                return {
                    'found': True,
                    'source': 'DOI Direct',
                    'pdf_url': final_url
                }

        # Note: Sci-Hub access is controversial and may be blocked
        # We'll skip this for now to avoid legal issues

        return {'found': False, 'source': 'DOI/Sci-Hub'}

    except Exception as e:
        print(f"   ❌ DOI search error: {str(e)}")
        return {'found': False, 'source': 'DOI/Sci-Hub', 'error': str(e)}

def search_ieee_acm_direct(title, authors=""):
    """
    Search IEEE and ACM digital libraries directly
    """
    try:
        session = get_robust_session()

        # IEEE Xplore
        if any(keyword in title.lower() for keyword in ['ieee', 'computing', 'network', 'algorithm']):
            print(f"   🔍 Searching IEEE Xplore...")
            ieee_query = '+'.join(title.split()[:5])
            ieee_url = f"https://ieeexplore.ieee.org/search/searchresult.jsp?newsearch=true&queryText={ieee_query}"

            try:
                response = session.get(ieee_url, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')

                    # Look for document links
                    for link in soup.find_all('a', href=re.compile(r'/document/\d+')):
                        doc_url = urljoin('https://ieeexplore.ieee.org', link.get('href'))
                        # IEEE papers usually require subscription
                        return {
                            'found': True,
                            'source': 'IEEE Xplore',
                            'pdf_url': doc_url
                        }
            except:
                pass

        # ACM Digital Library
        if any(keyword in title.lower() for keyword in ['acm', 'computing', 'software']):
            print(f"   🔍 Searching ACM Digital Library...")
            acm_query = title.replace(' ', '+')
            acm_url = f"https://dl.acm.org/action/doSearch?AllField={acm_query}"

            try:
                response = session.get(acm_url, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')

                    # Look for paper links
                    for link in soup.find_all('a', href=re.compile(r'/doi/')):
                        paper_url = urljoin('https://dl.acm.org', link.get('href'))
                        return {
                            'found': True,
                            'source': 'ACM Digital Library',
                            'pdf_url': paper_url
                        }
            except:
                pass

        return {'found': False, 'source': 'IEEE/ACM Direct'}

    except Exception as e:
        print(f"   ❌ IEEE/ACM search error: {str(e)}")
        return {'found': False, 'source': 'IEEE/ACM Direct', 'error': str(e)}

def main():
    # Ask user for CSV file path
    print("Enhanced PDF Downloader")
    print("=" * 50)
    csv_path = input("Enter the path to your CSV file: ").strip()

    # Remove quotes if user included them
    csv_path = csv_path.strip('"').strip("'")

    # Check if file exists
    if not os.path.exists(csv_path):
        print(f"❌ Error: File not found: {csv_path}")
        return

    try:
        df = pd.read_csv(csv_path)
        print(f"✅ Successfully loaded CSV with {len(df)} papers")

        # Check if the CSV has the expected columns
        required_columns = ['title']
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            print(f"❌ Error: Missing required columns: {missing_columns}")
            print(f"Available columns: {list(df.columns)}")
            return

        # Check if there's a pdf_downloaded column to filter by
        if 'pdf_downloaded' in df.columns:
            # Filter papers that don't have PDFs yet
            failed_papers = df[df['pdf_downloaded'] == False].copy()
            print(f"Found {len(failed_papers)} papers without PDFs (filtering by pdf_downloaded=False)")
        else:
            # Use all papers if no pdf_downloaded column exists
            failed_papers = df.copy()
            print(f"No 'pdf_downloaded' column found, processing all {len(failed_papers)} papers")

        if len(failed_papers) == 0:
            print("✅ All papers already have PDFs downloaded!")
            return

        print("Starting enhanced PDF search...")
        print("=" * 80)

        results = []
        successful_downloads = 0

        for index, row in failed_papers.iterrows():
            title = row['title']  # Changed from 'original_title'
            paper_id = row['paper_id']  # Changed from 'original_id'

            print(f"\n[{index + 1}/{len(failed_papers)}] Processing: {title[:60]}...")

            # First, retry Semantic Scholar if it failed due to rate limiting
            semantic_result = {'found': False}
            if 'API Error: 429' in str(row.get('api_response', '')):
                semantic_result = retry_failed_semantic_scholar(title)

            # Use existing data if Semantic Scholar worked before
            authors = row.get('authors', '') if pd.notna(row.get('authors')) else ""
            doi = row.get('doi', '') if pd.notna(row.get('doi')) else ""

            # If semantic scholar found the paper, use its data
            if semantic_result.get('found'):
                authors = semantic_result.get('authors', authors)
                doi = semantic_result.get('doi', doi)

                # Try to download from Semantic Scholar first if PDF URL is available
                if semantic_result.get('pdf_url'):
                    print(f"   📥 Found PDF in Semantic Scholar: {semantic_result['pdf_url']}")
                    # Download logic here...

            # Try enhanced search with multiple sources
            download_result = enhanced_pdf_search_and_download(title, authors, doi)

            if download_result['pdf_downloaded']:
                successful_downloads += 1

            # Combine results
            result = {
                'paper_id': paper_id,  # Changed from 'original_id'
                'title': title,  # Changed from 'original_title'
                'enhanced_search_result': download_result['pdf_downloaded'],
                'pdf_filename': download_result['pdf_filename'],
                'pdf_source': download_result.get('pdf_source', ''),
                'sources_tried': ', '.join(download_result.get('sources_tried', [])),
                'semantic_retry': semantic_result.get('found', False)
            }

            results.append(result)

            # Rate limiting
            time.sleep(3)

        # Save enhanced results
        results_df = pd.DataFrame(results)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"/Users/reddy/2025/ResearchHelper/results/enhanced_pdf_download_{timestamp}.csv"
        results_df.to_csv(output_path, index=False)

        print("\n" + "=" * 80)
        print("ENHANCED DOWNLOAD SUMMARY:")
        print(f"Papers processed: {len(failed_papers)}")
        print(f"Additional PDFs downloaded: {successful_downloads}")
        print(f"New download rate: {(successful_downloads/len(failed_papers)*100):.1f}%")
        print(f"Results saved to: {output_path}")
        print("=" * 80)

    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main()
