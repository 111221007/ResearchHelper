#!/usr/bin/env python3
"""
Research Paper Pipeline API (Cleaned)
=====================
This API fetches papers, extracts abstracts, and collects keywords from metadata.
It does not perform categorization or NLP-based extraction.
"""

from flask import Flask, request, jsonify, send_from_directory, send_file, Response, make_response
from flask_cors import CORS
import os
import queue
import requests
import time
import re
import urllib.parse
import xml.etree.ElementTree as ET
import json
import zipfile
from enhanced_pdf_downloader import EnhancedPDFDownloader
from category_keyword_extractor import CategoryKeywordExtractor

# ========== App Setup ==========
app = Flask(__name__)
CORS(app)
log_queue = queue.Queue()
extractor = CategoryKeywordExtractor()

# ========== Logging ==========
def stream_log(msg):
    """Log to both terminal and queue for live frontend updates."""
    print(msg)
    try:
        log_queue.put(msg)
    except Exception:
        pass

@app.route('/api/logs')
def stream_logs():
    """Stream logs to the frontend via Server-Sent Events."""
    def event_stream():
        while True:
            msg = log_queue.get()
            yield f"data: {msg}\n\n"
    return Response(event_stream(), content_type='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*'
    })

# ========== Utility Functions ==========
def get_session():
    """Create a requests session with browser-like headers."""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })
    return session

def calculate_similarity(title1, title2):
    """Calculate Jaccard similarity between two titles."""
    if not title1 or not title2:
        return 0.0
    words1 = set(title1.lower().split())
    words2 = set(title2.lower().split())
    if not words1 or not words2:
        return 0.0
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    return intersection / union if union > 0 else 0.0

# ========== Abstract Extraction ==========
def search_semantic_scholar(title):
    """Try to fetch abstract from Semantic Scholar API."""
    try:
        session = get_session()
        clean_title = re.sub(r'[^\w\s]', ' ', title).strip()
        url = f"https://api.semanticscholar.org/graph/v1/paper/search"
        params = {'query': clean_title, 'fields': 'title,abstract', 'limit': 5}
        response = session.get(url, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            papers = data.get('data', [])
            for paper in papers:
                if paper.get('abstract'):
                    similarity = calculate_similarity(title, paper.get('title', ''))
                    if similarity > 0.6:
                        return {'found': True, 'abstract': paper['abstract'], 'source': 'Semantic Scholar'}
        time.sleep(1)
    except Exception as e:
        print(f"Semantic Scholar error: {e}")
    return {'found': False, 'abstract': '', 'source': 'Semantic Scholar'}

def search_arxiv(title):
    """Try to fetch abstract from arXiv API."""
    try:
        session = get_session()
        clean_title = re.sub(r'[^\w\s]', ' ', title).strip()
        search_query = urllib.parse.quote(clean_title)
        url = f"http://export.arxiv.org/api/query?search_query=ti:{search_query}&max_results=5"
        response = session.get(url, timeout=30)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
                entry_title = entry.find('{http://www.w3.org/2005/Atom}title')
                summary = entry.find('{http://www.w3.org/2005/Atom}summary')
                if entry_title is not None and summary is not None:
                    similarity = calculate_similarity(title, entry_title.text.strip())
                    if similarity > 0.6:
                        return {'found': True, 'abstract': summary.text.strip(), 'source': 'arXiv'}
        time.sleep(1)
    except Exception as e:
        print(f"arXiv error: {e}")
    return {'found': False, 'abstract': '', 'source': 'arXiv'}

# ========== Main Endpoints ==========
@app.route('/')
def index():
    """Serve the frontend index.html."""
    stream_log("[DEBUG] Root endpoint '/' accessed (frontend loaded)")
    response = make_response(send_from_directory('.', 'index.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/api/fetch', methods=['POST'])
def fetch_papers():
    """Fetch papers from CrossRef based on keywords and filters."""
    stream_log("[DEBUG] /api/fetch endpoint called")
    try:
        data = request.json
        keyword = data.get('keyword', '').strip()
        additional_keyword = data.get('additional_keyword', '').strip()
        from_year = int(data.get('from_year', 2020))
        to_year = int(data.get('to_year', 2025))
        total_results = min(int(data.get('total_results', 20)), 100)
        title_filter = data.get('title_filter', True)
        paper_type_filter = data.get('paper_type_filter', True)

        stream_log(f"[DEBUG] Fetching papers: {keyword} + {additional_keyword}, {from_year}-{to_year}, {total_results} results")

        papers = []
        session = get_session()

        rows_per_request = 20
        offset = 0
        fetched_count = 0
        max_attempts = total_results * 3
        processed_count = 0

        keyword_lower = keyword.lower().strip()
        additional_keyword_lower = additional_keyword.lower().strip()

        while fetched_count < total_results and processed_count < max_attempts:
            try:
                remaining = total_results - fetched_count
                current_rows = min(rows_per_request, remaining * 2)

                if additional_keyword.strip():
                    url = f'https://api.crossref.org/works?query.title={urllib.parse.quote(keyword)}+{urllib.parse.quote(additional_keyword)}'
                else:
                    url = f'https://api.crossref.org/works?query.title={urllib.parse.quote(keyword)}'

                url += f'&filter=from-pub-date:{from_year},until-pub-date:{to_year}'
                if paper_type_filter:
                    url += ',type:journal-article,type:proceedings-article'
                url += f'&rows={current_rows}&offset={offset}&sort=relevance'

                stream_log(f"[DEBUG] Fetching batch: offset={offset}, rows={current_rows}")
                response = session.get(url, timeout=30)
                if not response.ok:
                    stream_log(f"[ERROR] CrossRef API returned status {response.status_code}")
                    break

                data_response = response.json()
                items = data_response.get('message', {}).get('items', [])

                stream_log(f"[DEBUG] Items fetched in this batch: {len(items)}")
                if not items:
                    stream_log("[DEBUG] No more items returned from CrossRef API.")
                    break

                for item in items:
                    processed_count += 1
                    if fetched_count >= total_results:
                        break

                    title = ''
                    if item.get('title') and len(item['title']) > 0:
                        title = item['title'][0] if isinstance(item['title'], list) else item['title']

                    if title_filter and title:
                        title_lower = title.lower()
                        keyword_in_title = keyword_lower in title_lower
                        additional_in_title = not additional_keyword_lower or additional_keyword_lower in title_lower

                        if not (keyword_in_title and additional_in_title):
                            continue

                    paper = extract_paper_info(item, fetched_count + 1)
                    papers.append(paper)
                    fetched_count += 1

                offset += current_rows
                time.sleep(0.2)

            except Exception as e:
                stream_log(f"[ERROR] Error fetching batch: {e}")
                break

        stream_log(f"[DEBUG] Total papers fetched: {len(papers)}")
        return jsonify({
            'success': True,
            'papers': papers,
            'total': len(papers),
            'message': f'Successfully fetched {len(papers)} papers'
        })

    except Exception as e:
        stream_log(f"[ERROR] Error in fetch_papers: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to fetch papers'
        }), 500

def extract_paper_info(item, paper_id):
    """Extract paper information from CrossRef item"""
    authors = []
    if item.get('author'):
        for author in item['author']:
            if author.get('given') and author.get('family'):
                authors.append(f"{author['given']} {author['family']}")
            elif author.get('family'):
                authors.append(author['family'])

    title = ''
    if item.get('title') and len(item['title']) > 0:
        title = item['title'][0] if isinstance(item['title'], list) else item['title']

    abstract = ''
    if item.get('abstract'):
        abstract = re.sub(r'<[^>]+>', '', item['abstract']).replace('\n', ' ').strip()

    journal = ''
    if item.get('container-title') and len(item['container-title']) > 0:
        journal = item['container-title'][0] if isinstance(item['container-title'], list) else item['container-title']

    year = ''
    if item.get('published-print', {}).get('date-parts'):
        year = str(item['published-print']['date-parts'][0][0])
    elif item.get('published-online', {}).get('date-parts'):
        year = str(item['published-online']['date-parts'][0][0])

    return {
        'paper_id': f"paper_{str(paper_id).zfill(3)}",
        'title': title,
        'abstract': abstract,
        'authors': '; '.join(authors) if authors else 'Not Available',
        'journal': journal,
        'year': year,
        'volume': item.get('volume', ''),
        'issue': item.get('issue', ''),
        'pages': item.get('page', ''),
        'publisher': item.get('publisher', ''),
        'doi': item.get('DOI', ''),
        'url': item.get('URL', ''),
        'type': item.get('type', '')
    }

@app.route('/api/deduplicate', methods=['POST'])
def deduplicate_papers():
    try:
        data = request.get_json()
        papers = data.get('papers', [])

        if not papers:
            return jsonify({'error': 'No papers provided'}), 400

        unique_papers = []
        seen_dois = set()
        seen_titles = set()
        removed_count = 0

        for paper in papers:
            is_duplicate = False
            doi = paper.get('doi', '').strip()
            if doi and doi in seen_dois:
                is_duplicate = True
            title = paper.get('title', '').strip().lower()
            if title:
                title_words = set(title.split())
                for seen_title in seen_titles:
                    seen_words = set(seen_title.split())
                    if len(title_words) > 0 and len(seen_words) > 0:
                        overlap = len(title_words.intersection(seen_words))
                        similarity = overlap / max(len(title_words), len(seen_words))
                        if similarity > 0.8:
                            is_duplicate = True
                            break
            if not is_duplicate:
                unique_papers.append(paper)
                if doi:
                    seen_dois.add(doi)
                if title:
                    seen_titles.add(title)
            else:
                removed_count += 1

        stream_log(f"[DEBUG] Deduplication complete: {removed_count} duplicates removed, {len(unique_papers)} unique papers remaining")

        return jsonify({
            'success': True,
            'papers': unique_papers,
            'removed': removed_count,
            'removed_count': removed_count,
            'remaining': len(unique_papers),
            'deduplicated_count': len(unique_papers),
            'original_count': len(papers),
            'message': f'{removed_count} duplicates removed, {len(unique_papers)} unique papers remaining'
        })

    except Exception as e:
        stream_log(f"[ERROR] Deduplication error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/extract-abstracts', methods=['POST'])
def extract_abstracts():
    """Extract abstracts from multiple sources"""
    try:
        data = request.get_json()
        papers = data.get('papers', [])

        if not papers:
            return jsonify({'error': 'No papers provided'}), 400

        found_abstracts = 0

        for i, paper in enumerate(papers):
            stream_log(f"[DEBUG] Processing paper {i+1}/{len(papers)}: {paper.get('title', 'No title')[:50]}...")

            # Skip if already has abstract
            if paper.get('abstract') and paper['abstract'].strip():
                found_abstracts += 1
                continue

            title = paper.get('title', '')
            abstract_found = False

            # Try Semantic Scholar first
            if title:
                try:
                    result = search_semantic_scholar(title)
                    if result.get('found') and result.get('abstract'):
                        paper['abstract'] = result['abstract']
                        paper['abstract_source'] = 'Semantic Scholar'
                        paper['abstract_confidence'] = 'high'
                        abstract_found = True
                        found_abstracts += 1
                        stream_log(f"[DEBUG] Found abstract via Semantic Scholar for paper {i+1}")
                except Exception as e:
                    print(f"[ERROR] Semantic Scholar error for paper {i+1}: {e}")

            # Try arXiv if no abstract found
            if not abstract_found and title:
                try:
                    result = search_arxiv(title)
                    if result.get('found') and result.get('abstract'):
                        paper['abstract'] = result['abstract']
                        paper['abstract_source'] = 'arXiv'
                        paper['abstract_confidence'] = 'medium'
                        abstract_found = True
                        found_abstracts += 1
                        stream_log(f"[DEBUG] Found abstract via arXiv for paper {i+1}")
                except Exception as e:
                    print(f"[ERROR] arXiv error for paper {i+1}: {e}")

            # Set default values if no abstract found
            if not abstract_found:
                paper['abstract_source'] = 'none'
                paper['abstract_confidence'] = 'none'

        stream_log(f"[DEBUG] Abstract extraction complete: {found_abstracts}/{len(papers)} papers now have abstracts")

        return jsonify({
            'papers': papers,
            'found': found_abstracts,
            'total': len(papers)
        })

    except Exception as e:
        print(f"[ERROR] Abstract extraction error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/process-complete', methods=['POST'])
def process_complete():
    """Process papers: deduplicate, extract abstracts, categorize"""
    try:
        data = request.json
        papers = data.get('papers', [])

        if not papers:
            return jsonify({'success': False, 'error': 'No papers provided'}), 400

        print(f"Processing {len(papers)} papers...")

        # Simple deduplication based on title similarity
        unique_papers = []
        seen_titles = []

        for paper in papers:
            title = paper.get('title', '').strip()
            is_duplicate = False

            for seen_title in seen_titles:
                if calculate_similarity(title, seen_title) > 0.8:
                    is_duplicate = True
                    break

            if not is_duplicate:
                seen_titles.append(title)
                unique_papers.append(paper)

        # Process each unique paper
        processed_papers = []

        for i, paper in enumerate(unique_papers):
            print(f"Processing paper {i+1}/{len(unique_papers)}: {paper.get('title', '')[:50]}...")

            # Extract abstract if not available
            if not paper.get('abstract') or len(paper['abstract'].strip()) < 50:
                # Try Semantic Scholar first
                result = search_semantic_scholar(paper.get('title', ''))
                if result['found']:
                    paper['abstract'] = result['abstract']
                    paper['abstract_source'] = result['source']
                    paper['abstract_confidence'] = 'high'
                else:
                    # Try arXiv
                    result = search_arxiv(paper.get('title', ''))
                    if result['found']:
                        paper['abstract'] = result['abstract']
                        paper['abstract_source'] = result['source']
                        paper['abstract_confidence'] = 'high'
                    else:
                        paper['abstract_source'] = 'Not found'
                        paper['abstract_confidence'] = 'low'
            else:
                paper['abstract_source'] = 'Original'
                paper['abstract_confidence'] = 'high'

            # Just fetch the keywords from the paper metadata if available
            keywords = ''
            if 'keywords' in paper and paper['keywords']:
                keywords = paper['keywords']
            elif 'original_keywords' in paper and paper['original_keywords']:
                keywords = paper['original_keywords']
            elif 'keyword' in paper and paper['keyword']:
                keywords = paper['keyword']
            else:
                keywords = ''
            paper['original_keywords'] = keywords
            # Remove categorization logic and NLTK dependency
            paper['original_category'] = ''
            paper['contributions'] = ''
            paper['limitations'] = ''

            processed_papers.append(paper)

        return jsonify({
            'success': True,
            'papers': processed_papers,
            'original_count': len(papers),
            'deduplicated_count': len(unique_papers),
            'processed_count': len(processed_papers),
            'message': f'Successfully processed {len(processed_papers)} papers'
        })

    except Exception as e:
        stream_log(f"Processing error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/process-stream', methods=['POST'])
def process_stream():
    """Stream processing progress in real-time"""
    try:
        data = request.json
        papers = data.get('papers', [])

        if not papers:
            return jsonify({'success': False, 'error': 'No papers provided'}), 400

        def generate():
            yield f"data: {json.dumps({'type': 'start', 'message': f'Processing {len(papers)} papers...'})}\n\n"

            # Simple deduplication based on title similarity
            unique_papers = []
            seen_titles = []

            for paper in papers:
                title = paper.get('title', '').strip()
                is_duplicate = False

                for seen_title in seen_titles:
                    if calculate_similarity(title, seen_title) > 0.8:
                        is_duplicate = True
                        break

                if not is_duplicate:
                    seen_titles.append(title)
                    unique_papers.append(paper)

            yield f"data: {json.dumps({'type': 'dedup', 'message': f'Deduplicated: {len(unique_papers)} unique papers from {len(papers)} total'})}\n\n"

            # Process each unique paper
            processed_papers = []

            for i, paper in enumerate(unique_papers):
                title = paper.get('title', '')
                short_title = title[:70] + '...' if len(title) > 70 else title

                yield f"data: {json.dumps({'type': 'processing', 'message': f'Processing paper {i+1}/{len(unique_papers)}: {short_title}'})}\n\n"

                # Extract abstract if not available
                if not paper.get('abstract') or len(paper['abstract'].strip()) < 50:
                    yield f"data: {json.dumps({'type': 'abstract', 'message': f'Searching for abstract for paper {i+1}...'})}\n\n"

                    # Try Semantic Scholar first
                    result = search_semantic_scholar(paper.get('title', ''))
                    if result['found']:
                        paper['abstract'] = result['abstract']
                        paper['abstract_source'] = result['source']
                        paper['abstract_confidence'] = 'high'
                        message = f'Abstract found via {result["source"]} for paper {i+1}'
                        yield f"data: {json.dumps({'type': 'abstract', 'message': message})}\n\n"
                    else:
                        # Try arXiv
                        result = search_arxiv(paper.get('title', ''))
                        if result['found']:
                            paper['abstract'] = result['abstract']
                            paper['abstract_source'] = result['source']
                            paper['abstract_confidence'] = 'high'
                            message = f'Abstract found via {result["source"]} for paper {i+1}'
                            yield f"data: {json.dumps({'type': 'abstract', 'message': message})}\n\n"
                        else:
                            paper['abstract_source'] = 'Not found'
                            paper['abstract_confidence'] = 'low'
                            yield f"data: {json.dumps({'type': 'abstract', 'message': f'No abstract found for paper {i+1}'})}\n\n"
                else:
                    paper['abstract_source'] = 'Original'
                    paper['abstract_confidence'] = 'high'

                # Just fetch the keywords from the paper metadata if available
                keywords = ''
                if 'keywords' in paper and paper['keywords']:
                    keywords = paper['keywords']
                elif 'original_keywords' in paper and paper['original_keywords']:
                    keywords = paper['original_keywords']
                elif 'keyword' in paper and paper['keyword']:
                    keywords = paper['keyword']
                else:
                    keywords = ''
                paper['original_keywords'] = keywords
                # Remove categorization logic and NLTK dependency
                paper['original_category'] = ''
                paper['contributions'] = ''
                paper['limitations'] = ''

                processed_papers.append(paper)

                yield f"data: {json.dumps({'type': 'complete', 'message': f'Completed paper {i+1}/{len(unique_papers)}'})}\n\n"

            yield f"data: {json.dumps({'type': 'finished', 'papers': processed_papers, 'total': len(processed_papers)})}\n\n"

        return Response(generate(), content_type='text/event-stream', headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*'
        })

    except Exception as e:
        stream_log(f"Processing error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/download-pdfs', methods=['POST'])
def download_pdfs():
    """Download PDFs for a list of papers and return a ZIP file"""
    try:
        stream_log("[DEBUG] PDF download endpoint called")
        data = request.get_json()
        papers = data.get('papers', [])
        stream_log(f"[DEBUG] Number of papers to download: {len(papers)}")

        if not papers:
            stream_log("[ERROR] No papers provided for PDF download")
            return jsonify({'success': False, 'error': 'No papers provided'}), 400

        # Use EnhancedPDFDownloader
        stream_log("[DEBUG] Initializing EnhancedPDFDownloader")
        downloader = EnhancedPDFDownloader()
        pdf_dir = downloader.pdf_dir
        stream_log(f"[DEBUG] PDF directory: {pdf_dir}")
        os.makedirs(pdf_dir, exist_ok=True)
        results = []

        stream_log("[DEBUG] Starting PDF download process")
        for i, paper in enumerate(papers):
            paper_id = paper.get('paper_id') or paper.get('id') or paper.get('doi') or paper.get('title', 'paper')
            pdf_url = paper.get('url') or paper.get('pdf_url') or ''
            stream_log(f"[DEBUG] Processing paper {i+1}/{len(papers)}: {paper_id[:50]}...")
            stream_log(f"[DEBUG] PDF URL: {pdf_url[:100] if pdf_url else 'No URL'}")

            # Try to download using the enhanced method
            success, filepath, msg = downloader.download_pdf_for_paper(paper)
            stream_log(f"[DEBUG] Download result: success={success}, filepath={filepath}, msg={msg}")
            results.append({'paper_id': paper_id, 'success': success, 'filepath': filepath, 'msg': msg})

        stream_log(f"[DEBUG] Download attempts completed. Creating ZIP file...")
        successful_downloads = [r for r in results if r['success']]
        stream_log(f"[DEBUG] Successful downloads: {len(successful_downloads)}/{len(results)}")

        # Create ZIP of all successfully downloaded PDFs
        zip_path = os.path.join(pdf_dir, 'papers_pdfs.zip')
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for r in results:
                if r['success'] and r['filepath'] and os.path.exists(r['filepath']):
                    stream_log(f"[DEBUG] Adding {r['filepath']} to ZIP")
                    zipf.write(r['filepath'], os.path.basename(r['filepath']))

        stream_log(f"[DEBUG] ZIP file created: {zip_path}")
        zip_size = os.path.getsize(zip_path) if os.path.exists(zip_path) else 0
        stream_log(f"[DEBUG] ZIP file size: {zip_size} bytes")

        if zip_size == 0:
            stream_log("[WARNING] ZIP file is empty - no PDFs were downloaded")
            return jsonify({
                'success': False,
                'error': 'No PDFs were found/downloadable',
                'results': results
            }), 404

        # Return ZIP file
        stream_log("[DEBUG] Sending ZIP file to client")
        return send_file(zip_path, as_attachment=True, download_name='papers_pdfs.zip')

    except Exception as e:
        stream_log(f"[ERROR] PDF download error: {e}")
        import traceback
        stream_log(f"[ERROR] Traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/download-pdfs-stream', methods=['POST'])
def download_pdfs_stream():
    """Stream PDF download progress and return ZIP file info"""
    try:
        data = request.get_json()
        papers = data.get('papers', [])

        if not papers:
            return jsonify({'success': False, 'error': 'No papers provided'}), 400

        def generate():
            yield f"data: {json.dumps({'type': 'start', 'message': f'Starting PDF download for {len(papers)} papers...'})}\n\n"

            # Create temporary directory for PDFs
            import tempfile
            pdf_dir = tempfile.mkdtemp()
            results = []
            successful_downloads = 0

            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })

            for i, paper in enumerate(papers):
                paper_id = paper.get('paper_id', f'paper_{i+1}')
                title = paper.get('title', 'Unknown Title')
                safe_title = re.sub(r'[^\w\s-]', '', title)[:50]

                yield f"data: {json.dumps({'type': 'processing', 'message': f'Processing paper {i+1}/{len(papers)}: {title[:60]}...'})}\n\n"

                pdf_downloaded = False
                pdf_path = None

                # Try multiple sources for PDF download
                sources_to_try = []

                # 1. Direct URL from paper data
                if paper.get('url'):
                    sources_to_try.append(('Direct URL', paper.get('url')))

                # 2. DOI-based download attempts
                doi = paper.get('doi', '')
                if doi:
                    # Try Unpaywall API
                    sources_to_try.append(('Unpaywall', f'https://api.unpaywall.org/v2/{doi}?email=research@example.com'))
                    # Try DOI redirect
                    sources_to_try.append(('DOI Redirect', f'https://doi.org/{doi}'))

                # 3. arXiv if detected
                if 'arxiv' in title.lower() or (paper.get('url') and 'arxiv.org' in paper.get('url')):
                    # Extract arXiv ID and construct PDF URL
                    arxiv_id = None
                    if paper.get('url') and 'arxiv.org' in paper.get('url'):
                        arxiv_match = re.search(r'arxiv\.org/abs/([^/\s]+)', paper.get('url'))
                        if arxiv_match:
                            arxiv_id = arxiv_match.group(1)

                    if arxiv_id:
                        sources_to_try.append(('arXiv', f'https://arxiv.org/pdf/{arxiv_id}.pdf'))

                # Try each source
                for source_name, url in sources_to_try:
                    if pdf_downloaded:
                        break

                    try:
                        yield f"data: {json.dumps({'type': 'processing', 'message': f'Trying {source_name} for: {safe_title}'})}\n\n"

                        if source_name == 'Unpaywall':
                            # Special handling for Unpaywall API
                            response = session.get(url, timeout=30)
                            if response.status_code == 200:
                                unpaywall_data = response.json()
                                if unpaywall_data.get('is_oa') and unpaywall_data.get('best_oa_location'):
                                    pdf_url = unpaywall_data['best_oa_location'].get('url_for_pdf')
                                    if pdf_url:
                                        url = pdf_url
                                    else:
                                        continue
                                else:
                                    continue

                        # Download the actual PDF
                        response = session.get(url, timeout=60, stream=True)
                        if response.status_code == 200:
                            content_type = response.headers.get('content-type', '').lower()

                            # Check if it's likely a PDF
                            if 'application/pdf' in content_type or url.endswith('.pdf'):
                                # Save the PDF
                                pdf_filename = f"{safe_title}_{paper_id}.pdf"
                                pdf_path = os.path.join(pdf_dir, pdf_filename)

                                with open(pdf_path, 'wb') as f:
                                    for chunk in response.iter_content(chunk_size=8192):
                                        if chunk:
                                            f.write(chunk)

                                # Verify it's a valid PDF
                                if os.path.getsize(pdf_path) > 1000:  # At least 1KB
                                    with open(pdf_path, 'rb') as f:
                                        header = f.read(8)
                                        if header.startswith(b'%PDF-'):
                                            pdf_downloaded = True
                                            successful_downloads += 1
                                            file_size = os.path.getsize(pdf_path) / (1024 * 1024)  # MB
                                            yield f"data: {json.dumps({'type': 'success', 'message': f'✅ Downloaded: {safe_title} ({file_size:.1f}MB) from {source_name}'})}\n\n"
                                            break

                                # Remove invalid file
                                if not pdf_downloaded and os.path.exists(pdf_path):
                                    os.remove(pdf_path)
                                    pdf_path = None

                        time.sleep(0.5)  # Rate limiting

                    except Exception as e:
                        yield f"data: {json.dumps({'type': 'failed', 'message': f'❌ {source_name} failed for {safe_title}: {str(e)}'})}\n\n"
                        continue

                if not pdf_downloaded:
                    yield f"data: {json.dumps({'type': 'failed', 'message': f'❌ No PDF found for: {safe_title}'})}\n\n"

                results.append({
                    'paper_id': paper_id,
                    'success': pdf_downloaded,
                    'filepath': pdf_path,
                    'title': safe_title
                })

            # Create ZIP file with actual PDFs
            if successful_downloads > 0:
                yield f"data: {json.dumps({'type': 'creating_zip', 'message': f'Creating ZIP file with {successful_downloads} actual PDFs...'})}\n\n"

                try:
                    zip_path = os.path.join(pdf_dir, 'research_papers.zip')
                    with zipfile.ZipFile(zip_path, 'w') as zipf:
                        for result in results:
                            if result['success'] and result['filepath'] and os.path.exists(result['filepath']):
                                # Add actual PDF file to ZIP
                                zipf.write(result['filepath'], f"{result['title']}.pdf")

                    zip_size = os.path.getsize(zip_path) if os.path.exists(zip_path) else 0
                    yield f"data: {json.dumps({'type': 'complete', 'message': f'✅ ZIP created with {successful_downloads} actual PDF files ({zip_size/1024/1024:.1f}MB)', 'zip_path': 'research_papers.zip', 'successful': successful_downloads, 'total': len(papers)})}\n\n"

                except Exception as e:
                    yield f"data: {json.dumps({'type': 'error', 'message': f'❌ Error creating ZIP: {str(e)}'})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'complete', 'message': '⚠️ No actual PDFs were downloaded successfully', 'successful': 0, 'total': len(papers)})}\n\n"

        return Response(generate(), content_type='text/event-stream', headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*'
        })

    except Exception as e:
        stream_log(f"[ERROR] PDF download stream error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/download-zip/<path:zip_name>')
def download_zip_file(zip_name):
    """Download the created ZIP file"""
    try:
        # Check multiple possible locations for the ZIP file
        possible_paths = [
            # From EnhancedPDFDownloader
            os.path.join('/Users/reddy/2025/ResearchHelper/results/pdf', zip_name),
            # From temporary directory (streaming download)
            os.path.join('/tmp', zip_name),
            # In current directory
            os.path.join('.', zip_name)
        ]

        # Also check temp directories for recent ZIP files
        import tempfile
        import glob
        temp_zips = glob.glob(os.path.join(tempfile.gettempdir(), '**/research_papers.zip'), recursive=True)
        temp_zips.extend(glob.glob(os.path.join(tempfile.gettempdir(), '**/papers_pdfs.zip'), recursive=True))

        # Add found temp files to possible paths
        possible_paths.extend(temp_zips)

        stream_log(f"[DEBUG] Looking for ZIP file: {zip_name}")
        stream_log(f"[DEBUG] Checking paths: {possible_paths}")

        for zip_path in possible_paths:
            if os.path.exists(zip_path):
                file_size = os.path.getsize(zip_path)
                stream_log(f"[DEBUG] Found ZIP file: {zip_path}, size: {file_size} bytes")

                # Verify it's not empty and contains actual files
                if file_size > 100:  # At least 100 bytes
                    try:
                        with zipfile.ZipFile(zip_path, 'r') as zf:
                            file_list = zf.namelist()
                            stream_log(f"[DEBUG] ZIP contains: {file_list}")

                            # Check if it contains PDF files, not just text files
                            pdf_files = [f for f in file_list if f.endswith('.pdf')]
                            if pdf_files:
                                stream_log(f"[DEBUG] ZIP contains {len(pdf_files)} PDF files")
                                return send_file(zip_path, as_attachment=True, download_name='research_papers.zip')
                            else:
                                stream_log(f"[DEBUG] ZIP contains no PDF files, only: {file_list}")
                    except Exception as e:
                        stream_log(f"[DEBUG] Error reading ZIP file {zip_path}: {e}")
                        continue

        # If no valid ZIP found, return error
        stream_log(f"[ERROR] No valid ZIP file found for: {zip_name}")
        return jsonify({
            'success': False,
            'error': 'ZIP file not found or contains no PDF files',
            'message': 'The PDF download may have failed. Please try downloading PDFs again.'
        }), 404

    except Exception as e:
        stream_log(f"[ERROR] ZIP download error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/categorize', methods=['POST'])
def categorize_endpoint():
    """Categorize papers based on title and abstract, and add contributions/limitations using advanced extractor"""
    try:
        stream_log("[DEBUG] /api/categorize endpoint called")
        data = request.get_json()
        papers = data.get('papers', [])
        stream_log(f"[DEBUG] Number of papers received for categorization: {len(papers)}")
        if not papers:
            stream_log("[DEBUG] No papers provided to categorize.")
            return jsonify({'success': False, 'error': 'No papers provided'}), 400

        for idx, paper in enumerate(papers):
            title = paper.get('title', '')
            abstract = paper.get('abstract', '')
            stream_log(f"[DEBUG] Categorizing paper {idx+1}/{len(papers)}: {title[:60]}")
            # Use advanced extractor for category and keywords
            cat_result = extractor.categorize_paper(title, abstract)
            paper['original_category'] = cat_result.get('original_category', 'Others')
            paper['original_keywords'] = cat_result.get('original_keywords', '')
            # Use advanced extractor for contributions and limitations
            paper['contributions'] = extractor.extract_contributions(abstract)
            paper['limitations'] = extractor.extract_limitations(abstract)
        stream_log(f"[DEBUG] Categorization complete for {len(papers)} papers.")
        return jsonify({'success': True, 'papers': papers})
    except Exception as e:
        stream_log(f"[ERROR] Unsupervised categorization error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print("\n==============================")
    print("🚀 Starting Research Paper Pipeline Server on port 8000")
    print("==============================\n")
    app.run(host='0.0.0.0', port=8000, debug=True)

# For Vercel deployment
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
