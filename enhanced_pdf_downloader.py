#!/usr/bin/env python3
"""
Enhanced PDF Downloader for Research Papers
Downloads PDFs from multiple sources with advanced fallback mechanisms
"""

import pandas as pd
import requests
import time
import os
import re
from datetime import datetime
from urllib.parse import urljoin
from typing import Dict, Optional, Tuple
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
from bs4 import BeautifulSoup

class EnhancedPDFDownloader:
    def __init__(self, output_dir: str = "/Users/reddy/2025/ResearchHelper/results"):
        self.output_dir = output_dir
        self.pdf_dir = os.path.join(output_dir, "pdf")
        os.makedirs(self.pdf_dir, exist_ok=True)

        # Setup logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

        # Rate limiting
        self.last_request_time = 0
        self.min_delay = 0.5

        # Session for persistent connections
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

        # Download statistics
        self.stats = {
            'total_attempts': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'semantic_scholar_success': 0,
            'arxiv_success': 0,
            'direct_url_success': 0,
            'doi_redirect_success': 0,
            'web_scraping_success': 0
        }

    def rate_limit(self):
        """Implement rate limiting between requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_delay:
            time.sleep(self.min_delay - time_since_last)
        self.last_request_time = time.time()

    def download_pdf(self, paper_id: str, pdf_url: str, max_size_mb: int = 50) -> Tuple[bool, str, str]:
        """Download PDF from URL with validation"""
        if not pdf_url:
            return False, "", "No PDF URL provided"

        try:
            self.rate_limit()

            # Head request first to check content type and size
            head_response = self.session.head(pdf_url, timeout=30, allow_redirects=True)

            content_type = head_response.headers.get('content-type', '').lower()
            if 'application/pdf' not in content_type and 'pdf' not in content_type:
                return False, "", f"Invalid content type: {content_type}"

            content_length = head_response.headers.get('content-length')
            if content_length and int(content_length) > max_size_mb * 1024 * 1024:
                return False, "", f"File too large: {int(content_length)/(1024*1024):.1f}MB"

            # Download the file
            response = self.session.get(pdf_url, timeout=60, stream=True)
            response.raise_for_status()

            # Create filename
            filename = f"{paper_id}.pdf"
            filepath = os.path.join(self.pdf_dir, filename)

            # Download with progress tracking
            downloaded_size = 0
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)

                        # Check size limit during download
                        if downloaded_size > max_size_mb * 1024 * 1024:
                            f.close()
                            os.remove(filepath)
                            return False, "", f"File too large during download: {downloaded_size/(1024*1024):.1f}MB"

            # Verify file size and content
            if os.path.getsize(filepath) < 1000:  # Less than 1KB
                os.remove(filepath)
                return False, "", "Downloaded file too small"

            # Basic PDF validation
            with open(filepath, 'rb') as f:
                header = f.read(8)
                if not header.startswith(b'%PDF-'):
                    os.remove(filepath)
                    return False, "", "Invalid PDF file format"

            return True, filepath, f"Successfully downloaded {downloaded_size/(1024*1024):.1f}MB"

        except Exception as e:
            return False, "", f"Download error: {str(e)}"

    def search_semantic_scholar_pdf(self, title: str, doi: str = "") -> Optional[str]:
        """Search Semantic Scholar for PDF link"""
        try:
            self.rate_limit()

            # Search by DOI first if available
            if doi:
                search_url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}"
                params = {'fields': 'openAccessPdf,url'}
            else:
                # Search by title
                clean_title = re.sub(r'[^\w\s]', ' ', title).strip()
                search_url = f"https://api.semanticscholar.org/graph/v1/paper/search"
                params = {
                    'query': clean_title,
                    'fields': 'openAccessPdf,url,title',
                    'limit': 5
                }

            response = self.session.get(search_url, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()

                if doi and data.get('openAccessPdf', {}).get('url'):
                    return data['openAccessPdf']['url']
                elif not doi and data.get('data'):
                    # Find best title match
                    for paper in data['data']:
                        paper_title = paper.get('title', '')
                        if self.title_similarity(title, paper_title) > 0.8:
                            pdf_info = paper.get('openAccessPdf', {})
                            if pdf_info and pdf_info.get('url'):
                                return pdf_info['url']

        except Exception as e:
            self.logger.error(f"Semantic Scholar PDF search error: {e}")

        return None

    def get_arxiv_pdf_url(self, url: str) -> Optional[str]:
        """Convert arXiv abstract URL to PDF URL"""
        if not url or 'arxiv.org' not in url:
            return None

        try:
            # Extract arXiv ID from URL
            arxiv_id_match = re.search(r'arxiv\.org/abs/([^/\s]+)', url)
            if arxiv_id_match:
                arxiv_id = arxiv_id_match.group(1)
                return f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        except Exception as e:
            self.logger.error(f"arXiv URL conversion error: {e}")

        return None

    def get_doi_redirect_url(self, doi: str) -> Optional[str]:
        """Try to get PDF URL from DOI redirect"""
        if not doi:
            return None

        try:
            self.rate_limit()

            doi_url = f"https://doi.org/{doi}"
            response = self.session.head(doi_url, timeout=30, allow_redirects=True)

            final_url = response.url

            # Check if final URL looks like it might have PDF
            if any(indicator in final_url.lower() for indicator in ['pdf', 'download', 'view']):
                return final_url

            # Try adding common PDF suffixes
            possible_urls = [
                final_url + '.pdf',
                final_url + '/pdf',
                final_url.replace('/abstract/', '/pdf/'),
                final_url.replace('/article/', '/pdf/')
            ]

            for url in possible_urls:
                try:
                    head_resp = self.session.head(url, timeout=10)
                    if head_resp.status_code == 200:
                        content_type = head_resp.headers.get('content-type', '').lower()
                        if 'pdf' in content_type:
                            return url
                except:
                    continue

        except Exception as e:
            self.logger.error(f"DOI redirect error: {e}")

        return None

    def scrape_pdf_from_page(self, url: str) -> Optional[str]:
        """Scrape PDF link from paper page"""
        if not url:
            return None

        try:
            self.rate_limit()

            response = self.session.get(url, timeout=30)
            if response.status_code != 200:
                return None

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')

            # Common PDF link patterns
            pdf_selectors = [
                'a[href*=".pdf"]',
                'a[href*="pdf"]',
                'a[title*="PDF"]',
                'a[title*="Download"]',
                '.pdf-download a',
                '.download-pdf a',
                '.article-pdf a'
            ]

            for selector in pdf_selectors:
                elements = soup.select(selector)
                for element in elements:
                    href = element.get('href')
                    if href and ('.pdf' in href.lower() or 'pdf' in href.lower()):
                        # Convert relative URL to absolute
                        if href.startswith('//'):
                            href = 'https:' + href
                        elif href.startswith('/'):
                            href = urljoin(url, href)
                        elif not href.startswith('http'):
                            href = urljoin(url, href)

                        return href

        except Exception as e:
            self.logger.error(f"PDF scraping error: {e}")

        return None

    def title_similarity(self, title1: str, title2: str) -> float:
        """Calculate title similarity"""
        if not title1 or not title2:
            return 0.0

        words1 = set(re.findall(r'\w+', title1.lower()))
        words2 = set(re.findall(r'\w+', title2.lower()))

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0.0

    def download_paper_pdf(self, paper: Dict) -> Dict:
        """Download PDF for a single paper using multiple strategies"""
        paper_id = paper.get('paper_id', 'unknown')
        title = paper.get('title', '')
        doi = paper.get('doi', '')
        url = paper.get('url', '')

        self.stats['total_attempts'] += 1

        result = {
            'paper_id': paper_id,
            'pdf_downloaded': False,
            'pdf_path': '',
            'pdf_source': '',
            'download_error': '',
            'file_size_mb': 0
        }

        # Strategy 1: Direct URL (if it looks like a PDF)
        if url and ('.pdf' in url.lower() or url.endswith('.pdf')):
            success, path, message = self.download_pdf(paper_id, url)
            if success:
                result.update({
                    'pdf_downloaded': True,
                    'pdf_path': path,
                    'pdf_source': 'Direct URL',
                    'file_size_mb': round(os.path.getsize(path) / (1024*1024), 2)
                })
                self.stats['successful_downloads'] += 1
                self.stats['direct_url_success'] += 1
                return result

        # Strategy 2: arXiv PDF conversion
        if url and 'arxiv.org' in url:
            arxiv_pdf_url = self.get_arxiv_pdf_url(url)
            if arxiv_pdf_url:
                success, path, message = self.download_pdf(paper_id, arxiv_pdf_url)
                if success:
                    result.update({
                        'pdf_downloaded': True,
                        'pdf_path': path,
                        'pdf_source': 'arXiv',
                        'file_size_mb': round(os.path.getsize(path) / (1024*1024), 2)
                    })
                    self.stats['successful_downloads'] += 1
                    self.stats['arxiv_success'] += 1
                    return result

        # Strategy 3: Semantic Scholar
        semantic_pdf_url = self.search_semantic_scholar_pdf(title, doi)
        if semantic_pdf_url:
            success, path, message = self.download_pdf(paper_id, semantic_pdf_url)
            if success:
                result.update({
                    'pdf_downloaded': True,
                    'pdf_path': path,
                    'pdf_source': 'Semantic Scholar',
                    'file_size_mb': round(os.path.getsize(path) / (1024*1024), 2)
                })
                self.stats['successful_downloads'] += 1
                self.stats['semantic_scholar_success'] += 1
                return result

        # Strategy 4: DOI redirect
        if doi:
            doi_pdf_url = self.get_doi_redirect_url(doi)
            if doi_pdf_url:
                success, path, message = self.download_pdf(paper_id, doi_pdf_url)
                if success:
                    result.update({
                        'pdf_downloaded': True,
                        'pdf_path': path,
                        'pdf_source': 'DOI Redirect',
                        'file_size_mb': round(os.path.getsize(path) / (1024*1024), 2)
                    })
                    self.stats['successful_downloads'] += 1
                    self.stats['doi_redirect_success'] += 1
                    return result

        # Strategy 5: Web scraping
        if url:
            scraped_pdf_url = self.scrape_pdf_from_page(url)
            if scraped_pdf_url:
                success, path, message = self.download_pdf(paper_id, scraped_pdf_url)
                if success:
                    result.update({
                        'pdf_downloaded': True,
                        'pdf_path': path,
                        'pdf_source': 'Web Scraping',
                        'file_size_mb': round(os.path.getsize(path) / (1024*1024), 2)
                    })
                    self.stats['successful_downloads'] += 1
                    self.stats['web_scraping_success'] += 1
                    return result

        # If all strategies failed
        self.stats['failed_downloads'] += 1
        result['download_error'] = 'All download strategies failed'
        return result

    def download_pdf_for_paper(self, paper: dict) -> Tuple[bool, str, str]:
        """Try all sources to download PDF for a paper dict (title, url, doi, etc)"""
        title = paper.get('title', '')
        pdf_url = paper.get('url', '') or paper.get('pdf_url', '')
        doi = paper.get('doi', '')
        paper_id = paper.get('paper_id', '') or paper.get('id', '') or doi or title[:20]

        # 1. Try direct PDF URL
        if pdf_url:
            success, filepath, msg = self.download_pdf(paper_id, pdf_url)
            if success:
                return True, filepath, f"Direct PDF: {msg}"

        # 2. Try Semantic Scholar
        ss_pdf = self.search_semantic_scholar_pdf(title, doi)
        if ss_pdf:
            success, filepath, msg = self.download_pdf(paper_id, ss_pdf)
            if success:
                return True, filepath, f"Semantic Scholar: {msg}"

        # 3. Try arXiv (if arXiv in url or title)
        arxiv_url = None
        if 'arxiv.org' in pdf_url or 'arxiv' in title.lower():
            arxiv_url = self.get_arxiv_pdf_url(pdf_url)
            if not arxiv_url:
                # Try arXiv API/web scraping from 4_enhanced_pdf_downloader.py logic
                arxiv_result = search_arxiv_for_pdf(title)
                if arxiv_result and arxiv_result.get('found') and arxiv_result.get('pdf_url'):
                    arxiv_url = arxiv_result['pdf_url']
        if arxiv_url:
            success, filepath, msg = self.download_pdf(paper_id, arxiv_url)
            if success:
                return True, filepath, f"arXiv: {msg}"

        # 4. Try DOI redirect
        if doi:
            doi_pdf = self.get_doi_redirect_url(doi)
            if doi_pdf:
                success, filepath, msg = self.download_pdf(paper_id, doi_pdf)
                if success:
                    return True, filepath, f"DOI redirect: {msg}"

        # 5. Try Semantic Scholar fallback (from 4_enhanced_pdf_downloader.py)
        try:
            ss_result = search_semantic_scholar_with_fallback(title)
            if ss_result and ss_result.get('found') and ss_result.get('pdf_url'):
                success, filepath, msg = self.download_pdf(paper_id, ss_result['pdf_url'])
                if success:
                    return True, filepath, f"Semantic Scholar fallback: {msg}"
        except Exception as e:
            self.logger.error(f"Semantic Scholar fallback error: {e}")

        # 6. Web scraping fallback (future: publisher scraping)
        return False, "", "No PDF found from any source"

    def download_papers_batch(self, csv_path: str, max_workers: int = 3) -> str:
        """Download PDFs for all papers in CSV file"""
        # Read the CSV
        df = pd.read_csv(csv_path)
        self.logger.info(f"Starting PDF download for {len(df)} papers")

        # Initialize new columns
        df['pdf_downloaded'] = False
        df['pdf_path'] = ''
        df['pdf_source'] = ''
        df['download_error'] = ''
        df['file_size_mb'] = 0

        # Process papers with thread pool
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all download tasks
            future_to_idx = {
                executor.submit(self.download_paper_pdf, row.to_dict()): idx
                for idx, row in df.iterrows()
            }

            # Process completed tasks
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    result = future.result()
                    results.append((idx, result))

                    # Update progress
                    if len(results) % 10 == 0:
                        success_rate = self.stats['successful_downloads'] / self.stats['total_attempts'] * 100
                        self.logger.info(f"Processed {len(results)}/{len(df)} papers. Success rate: {success_rate:.1f}%")

                except Exception as e:
                    self.logger.error(f"Error processing paper {idx}: {e}")
                    results.append((idx, {
                        'paper_id': df.at[idx, 'paper_id'],
                        'pdf_downloaded': False,
                        'download_error': str(e)
                    }))

        # Update dataframe with results
        for idx, result in results:
            for key, value in result.items():
                if key in df.columns:
                    df.at[idx, key] = value

        # Save enhanced CSV
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"enhanced_papers_with_pdfs_{timestamp}.csv"
        output_path = os.path.join(self.output_dir, output_filename)
        df.to_csv(output_path, index=False)

        # Print summary
        self.print_download_summary(len(df))
        self.logger.info(f"Enhanced CSV with PDF info saved to: {output_path}")

        return output_path

    def print_download_summary(self, total_papers: int):
        """Print download statistics summary"""
        print(f"\n📊 PDF DOWNLOAD SUMMARY:")
        print(f"Total papers processed: {total_papers}")
        print(f"Download attempts: {self.stats['total_attempts']}")
        print(f"Successful downloads: {self.stats['successful_downloads']}")
        print(f"Failed downloads: {self.stats['failed_downloads']}")
        print(f"Success rate: {self.stats['successful_downloads']/self.stats['total_attempts']*100:.1f}%")
        print(f"\n📈 SUCCESS BY SOURCE:")
        print(f"Semantic Scholar: {self.stats['semantic_scholar_success']}")
        print(f"arXiv: {self.stats['arxiv_success']}")
        print(f"Direct URL: {self.stats['direct_url_success']}")
        print(f"DOI Redirect: {self.stats['doi_redirect_success']}")
        print(f"Web Scraping: {self.stats['web_scraping_success']}")

# --- Begin: Helper functions from 4_enhanced_pdf_downloader.py ---
def get_robust_session():
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"],
        backoff_factor=1
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
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
    try:
        session = get_robust_session()
        clean_title = re.sub(r'[^\w\s]', ' ', title).strip()
        clean_title = ' '.join(clean_title.split()[:8])
        arxiv_url = "http://export.arxiv.org/api/query"
        params = {
            'search_query': f'all:"{clean_title}"',
            'start': 0,
            'max_results': 5
        }
        response = session.get(arxiv_url, params=params, timeout=15)
        if response.status_code == 200:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.content)
            for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
                arxiv_title = entry.find('{http://www.w3.org/2005/Atom}title').text.strip()
                title_words = set(w.lower() for w in title.split() if len(w) > 3)
                arxiv_words = set(w.lower() for w in arxiv_title.split() if len(w) > 3)
                common_words = title_words.intersection(arxiv_words)
                if len(common_words) >= min(2, int(len(title_words) * 0.4)):
                    for link in entry.findall('{http://www.w3.org/2005/Atom}link'):
                        if link.get('type') == 'application/pdf':
                            pdf_url = link.get('href')
                            return {
                                'found': True,
                                'source': 'arXiv-API',
                                'title': arxiv_title,
                                'pdf_url': pdf_url
                            }
        # Web fallback
        search_terms = '+'.join(title.split()[:4])
        arxiv_search_url = f"https://arxiv.org/search/?query={search_terms}&searchtype=all"
        response = session.get(arxiv_search_url, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            for result in soup.find_all('li', class_='arxiv-result'):
                title_elem = result.find('p', class_='title')
                if title_elem:
                    arxiv_title = title_elem.get_text().strip()
                    if any(word.lower() in arxiv_title.lower() for word in title.split()[:3] if len(word) > 3):
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
        return {'found': False, 'source': 'arXiv', 'error': str(e)}

def search_semantic_scholar_with_fallback(title):
    try:
        session = get_robust_session()
        search_url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            'query': title,
            'limit': 3,
            'fields': 'paperId,title,abstract,year,authors,venue,url,openAccessPdf,isOpenAccess,externalIds'
        }
        import time
        time.sleep(random.uniform(3, 6))
        response = session.get(search_url, params=params, timeout=20)
        if response.status_code == 429:
            time.sleep(30)
            response = session.get(search_url, params=params, timeout=20)
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and len(data['data']) > 0:
                for paper in data['data']:
                    paper_title = paper.get('title', '')
                    if title.lower() in paper_title.lower() or paper_title.lower() in title.lower():
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
        return {'found': False, 'error': str(e)}
# --- End: Helper functions ---

if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python enhanced_pdf_downloader.py <csv_file_path>")
        sys.exit(1)

    csv_path = sys.argv[1]
    if not os.path.exists(csv_path):
        print(f"Error: File '{csv_path}' not found!")
        sys.exit(1)

    downloader = EnhancedPDFDownloader()
    try:
        output_path = downloader.download_papers_batch(csv_path, max_workers=3)
        print(f"\n✅ PDF download completed!")
        print(f"Enhanced CSV available at: {output_path}")
    except Exception as e:
        print(f"❌ Error: {e}")
