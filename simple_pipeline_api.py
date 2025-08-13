#!/usr/bin/env python3
"""
Research Paper Pipeline API - Original Working Version
Simple and reliable paper fetching and processing
"""

from flask import Flask, request, jsonify, send_from_directory, send_file, Response
from flask_cors import CORS
import os
import tempfile
import zipfile
import pandas as pd
from flask import Flask, request, jsonify, send_file
from enhanced_pdf_downloader import EnhancedPDFDownloader
import requests
import time
import re
import urllib.parse
import xml.etree.ElementTree as ET
import json
from category_keyword_extractor import CategoryKeywordExtractor
import subprocess

app = Flask(__name__)
CORS(app)

# Instantiate the advanced extractor
extractor = CategoryKeywordExtractor()

def get_session():
    """Create a session with proper headers"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })
    return session

def calculate_similarity(title1, title2):
    """Calculate similarity between titles"""
    if not title1 or not title2:
        return 0.0

    # Simple word-based similarity
    words1 = set(title1.lower().split())
    words2 = set(title2.lower().split())

    if not words1 or not words2:
        return 0.0

    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))

    return intersection / union if union > 0 else 0.0

def search_semantic_scholar(title):
    """Search Semantic Scholar for abstract"""
    try:
        session = get_session()
        clean_title = re.sub(r'[^\w\s]', ' ', title).strip()

        url = f"https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            'query': clean_title,
            'fields': 'title,abstract',
            'limit': 5
        }

        response = session.get(url, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            papers = data.get('data', [])

            for paper in papers:
                if paper.get('abstract'):
                    similarity = calculate_similarity(title, paper.get('title', ''))
                    if similarity > 0.6:
                        return {
                            'found': True,
                            'abstract': paper['abstract'],
                            'source': 'Semantic Scholar'
                        }

        time.sleep(1)  # Rate limiting

    except Exception as e:
        print(f"Semantic Scholar error: {e}")

    return {'found': False, 'abstract': '', 'source': 'Semantic Scholar'}

def search_arxiv(title):
    """Search arXiv for abstract"""
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
                        return {
                            'found': True,
                            'abstract': summary.text.strip(),
                            'source': 'arXiv'
                        }

        time.sleep(1)  # Rate limiting

    except Exception as e:
        print(f"arXiv error: {e}")

    return {'found': False, 'abstract': '', 'source': 'arXiv'}

def categorize_paper(title, abstract):
    """Simple categorization based on keywords"""
    text = f"{title} {abstract}".lower()

    categories = {
        'survey': ['survey', 'review', 'taxonomy'],
        'latency': ['latency', 'response time', 'cold start'],
        'security': ['security', 'privacy', 'authentication'],
        'cost': ['cost', 'pricing', 'billing'],
        'performance': ['performance', 'optimization', 'efficiency'],
        'serverless': ['serverless', 'lambda', 'function'],
        'others': []
    }

    found_categories = []
    found_keywords = []

    for category, keywords in categories.items():
        if category == 'others':
            continue
        for keyword in keywords:
            if keyword in text:
                if category not in found_categories:
                    found_categories.append(category)
                if keyword not in found_keywords:
                    found_keywords.append(keyword)

    if not found_categories:
        found_categories = ['others']

    return ', '.join(found_categories), ', '.join(found_keywords[:5])

@app.route('/')
def index():
    from flask import make_response
    response = make_response(send_from_directory('.', 'index.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/api/fetch', methods=['POST'])
def fetch_papers():
    print("[DEBUG] /api/fetch endpoint called")
    try:
        data = request.json
        keyword = data.get('keyword', '').strip()
        additional_keyword = data.get('additional_keyword', '').strip()
        from_year = int(data.get('from_year', 2020))
        to_year = int(data.get('to_year', 2025))
        total_results = min(int(data.get('total_results', 20)), 100)
        title_filter = data.get('title_filter', True)
        paper_type_filter = data.get('paper_type_filter', True)

        print(f"[DEBUG] Fetching papers: {keyword} + {additional_keyword}, {from_year}-{to_year}, {total_results} results")

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

                print(f"[DEBUG] Fetching batch: offset={offset}, rows={current_rows}, url={url}")
                response = session.get(url, timeout=30)
                if not response.ok:
                    print(f"[ERROR] CrossRef API returned status {response.status_code}")
                    break

                data_response = response.json()
                items = data_response.get('message', {}).get('items', [])

                print(f"[DEBUG] Items fetched in this batch: {len(items)}")
                if not items:
                    print("[DEBUG] No more items returned from CrossRef API.")
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
                print(f"[ERROR] Error fetching batch: {e}")
                break

        print(f"[DEBUG] Total papers fetched: {len(papers)}")
        return jsonify({
            'success': True,
            'papers': papers,
            'total': len(papers),
            'message': f'Successfully fetched {len(papers)} papers'
        })

    except Exception as e:
        print(f"[ERROR] Error in fetch_papers: {e}")
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
    """Remove duplicate papers based on title similarity and DOI"""
    try:
        data = request.get_json()
        papers = data.get('papers', [])

        if not papers:
            return jsonify({'error': 'No papers provided'}), 400

        # Deduplicate papers based on title similarity and DOI
        unique_papers = []
        seen_dois = set()
        seen_titles = set()
        removed_count = 0

        for paper in papers:
            is_duplicate = False

            # Check DOI duplication
            doi = paper.get('doi', '').strip()
            if doi and doi in seen_dois:
                is_duplicate = True

            # Check title similarity (simple word-based comparison)
            title = paper.get('title', '').strip().lower()
            if title:
                # Simple duplicate detection by exact title match
                title_words = set(title.split())
                for seen_title in seen_titles:
                    seen_words = set(seen_title.split())
                    # If 80% of words overlap, consider it duplicate
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

        print(f"[DEBUG] Deduplication complete: {removed_count} duplicates removed, {len(unique_papers)} unique papers remaining")

        return jsonify({
            'papers': unique_papers,
            'removed': removed_count,
            'remaining': len(unique_papers)
        })

    except Exception as e:
        print(f"[ERROR] Deduplication error: {e}")
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
            print(f"[DEBUG] Processing paper {i+1}/{len(papers)}: {paper.get('title', 'No title')[:50]}...")

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
                        print(f"[DEBUG] Found abstract via Semantic Scholar for paper {i+1}")
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
                        print(f"[DEBUG] Found abstract via arXiv for paper {i+1}")
                except Exception as e:
                    print(f"[ERROR] arXiv error for paper {i+1}: {e}")

            # Set default values if no abstract found
            if not abstract_found:
                paper['abstract_source'] = 'none'
                paper['abstract_confidence'] = 'none'

        print(f"[DEBUG] Abstract extraction complete: {found_abstracts}/{len(papers)} papers now have abstracts")

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

            # Categorize paper
            categories, keywords = categorize_paper(paper.get('title', ''), paper.get('abstract', ''))
            paper['original_category'] = categories
            paper['original_keywords'] = keywords

            # Generate contributions and limitations based on abstract
            abstract = paper.get('abstract', '')
            if len(abstract) > 50:
                # Simple keyword-based extraction for contributions
                if any(word in abstract.lower() for word in ['propose', 'present', 'introduce', 'develop', 'design']):
                    paper['contributions'] = "Novel approach and methodology presented"
                else:
                    paper['contributions'] = "Various contributions mentioned in the paper"

                # Simple keyword-based extraction for limitations
                if any(word in abstract.lower() for word in ['limitation', 'challenge', 'future work', 'improve']):
                    paper['limitations'] = "Limitations and future work discussed"
                else:
                    paper['limitations'] = "Not explicitly mentioned"
            else:
                paper['contributions'] = "Not available"
                paper['limitations'] = "Not available"

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
        print(f"Processing error: {e}")
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

                # Categorize paper
                categories, keywords = categorize_paper(paper.get('title', ''), paper.get('abstract', ''))
                paper['original_category'] = categories
                paper['original_keywords'] = keywords

                # Generate contributions and limitations based on abstract
                abstract = paper.get('abstract', '')
                if len(abstract) > 50:
                    if any(word in abstract.lower() for word in ['propose', 'present', 'introduce', 'develop', 'design']):
                        paper['contributions'] = "Novel approach and methodology presented"
                    else:
                        paper['contributions'] = "Various contributions mentioned in the paper"

                    if any(word in abstract.lower() for word in ['limitation', 'challenge', 'future work', 'improve']):
                        paper['limitations'] = "Limitations and future work discussed"
                    else:
                        paper['limitations'] = "Not explicitly mentioned"
                else:
                    paper['contributions'] = "Not available"
                    paper['limitations'] = "Not available"

                processed_papers.append(paper)

                yield f"data: {json.dumps({'type': 'complete', 'message': f'Completed paper {i+1}/{len(unique_papers)}'})}\n\n"

            yield f"data: {json.dumps({'type': 'finished', 'papers': processed_papers, 'total': len(processed_papers)})}\n\n"

        return Response(generate(), content_type='text/event-stream', headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*'
        })

    except Exception as e:
        print(f"Processing error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/download-pdfs', methods=['POST'])
def download_pdfs():
    """Download PDFs for a list of papers and return a ZIP file"""
    try:
        print("[DEBUG] PDF download endpoint called")
        data = request.get_json()
        papers = data.get('papers', [])
        print(f"[DEBUG] Number of papers to download: {len(papers)}")

        if not papers:
            print("[ERROR] No papers provided for PDF download")
            return jsonify({'success': False, 'error': 'No papers provided'}), 400

        # Use EnhancedPDFDownloader
        print("[DEBUG] Initializing EnhancedPDFDownloader")
        downloader = EnhancedPDFDownloader()
        pdf_dir = downloader.pdf_dir
        print(f"[DEBUG] PDF directory: {pdf_dir}")
        os.makedirs(pdf_dir, exist_ok=True)
        results = []

        print("[DEBUG] Starting PDF download process")
        for i, paper in enumerate(papers):
            paper_id = paper.get('paper_id') or paper.get('id') or paper.get('doi') or paper.get('title', 'paper')
            pdf_url = paper.get('url') or paper.get('pdf_url') or ''
            print(f"[DEBUG] Processing paper {i+1}/{len(papers)}: {paper_id[:50]}...")
            print(f"[DEBUG] PDF URL: {pdf_url[:100] if pdf_url else 'No URL'}")

            # Try to download using the enhanced method
            success, filepath, msg = downloader.download_pdf_for_paper(paper)
            print(f"[DEBUG] Download result: success={success}, filepath={filepath}, msg={msg}")
            results.append({'paper_id': paper_id, 'success': success, 'filepath': filepath, 'msg': msg})

        print(f"[DEBUG] Download attempts completed. Creating ZIP file...")
        successful_downloads = [r for r in results if r['success']]
        print(f"[DEBUG] Successful downloads: {len(successful_downloads)}/{len(results)}")

        # Create ZIP of all successfully downloaded PDFs
        zip_path = os.path.join(pdf_dir, 'papers_pdfs.zip')
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for r in results:
                if r['success'] and r['filepath'] and os.path.exists(r['filepath']):
                    print(f"[DEBUG] Adding {r['filepath']} to ZIP")
                    zipf.write(r['filepath'], os.path.basename(r['filepath']))

        print(f"[DEBUG] ZIP file created: {zip_path}")
        zip_size = os.path.getsize(zip_path) if os.path.exists(zip_path) else 0
        print(f"[DEBUG] ZIP file size: {zip_size} bytes")

        if zip_size == 0:
            print("[WARNING] ZIP file is empty - no PDFs were downloaded")
            return jsonify({
                'success': False,
                'error': 'No PDFs were found/downloadable',
                'results': results
            }), 404

        # Return ZIP file
        print("[DEBUG] Sending ZIP file to client")
        return send_file(zip_path, as_attachment=True, download_name='papers_pdfs.zip')

    except Exception as e:
        print(f"[ERROR] PDF download error: {e}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
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

            downloader = EnhancedPDFDownloader()
            pdf_dir = downloader.pdf_dir
            os.makedirs(pdf_dir, exist_ok=True)
            results = []
            successful_downloads = 0

            for i, paper in enumerate(papers):
                paper_id = paper.get('paper_id') or paper.get('id') or paper.get('doi') or paper.get('title', 'paper')
                title = paper.get('title', '')[:60] + '...' if len(paper.get('title', '')) > 60 else paper.get('title', '')

                yield f"data: {json.dumps({'type': 'processing', 'message': f'Downloading PDF {i+1}/{len(papers)}: {title}'})}\n\n"

                success, filepath, msg = downloader.download_pdf_for_paper(paper)
                results.append({'paper_id': paper_id, 'success': success, 'filepath': filepath, 'msg': msg})

                if success:
                    successful_downloads += 1
                    yield f"data: {json.dumps({'type': 'success', 'message': f'✅ Downloaded: {title}'})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'failed', 'message': f'❌ Failed: {title} - {msg}'})}\n\n"

            yield f"data: {json.dumps({'type': 'creating_zip', 'message': f'Creating ZIP file with {successful_downloads} PDFs...'})}\n\n"

            # Create ZIP of all successfully downloaded PDFs
            zip_path = os.path.join(pdf_dir, 'papers_pdfs.zip')
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for r in results:
                    if r['success'] and r['filepath'] and os.path.exists(r['filepath']):
                        zipf.write(r['filepath'], os.path.basename(r['filepath']))

            zip_size = os.path.getsize(zip_path) if os.path.exists(zip_path) else 0

            if zip_size > 0:
                yield f"data: {json.dumps({'type': 'complete', 'message': f'✅ ZIP created with {successful_downloads} PDFs ({zip_size/1024/1024:.1f}MB)', 'zip_path': zip_path, 'successful': successful_downloads, 'total': len(papers)})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'error', 'message': '❌ No PDFs were downloaded successfully', 'successful': 0, 'total': len(papers)})}\n\n"

        return Response(generate(), content_type='text/event-stream', headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*'
        })

    except Exception as e:
        print(f"[ERROR] PDF download stream error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/download-zip/<path:zip_name>')
def download_zip_file(zip_name):
    """Download the created ZIP file"""
    try:
        downloader = EnhancedPDFDownloader()
        zip_path = os.path.join(downloader.pdf_dir, zip_name)
        if os.path.exists(zip_path):
            return send_file(zip_path, as_attachment=True, download_name='research_papers.zip')
        else:
            return "ZIP file not found", 404
    except Exception as e:
        print(f"[ERROR] ZIP download error: {e}")
        return "Error downloading ZIP", 500

@app.route('/api/categorize', methods=['POST'])
def categorize_endpoint():
    """Categorize papers based on title and abstract, and add contributions/limitations using advanced extractor"""
    try:
        data = request.get_json()
        papers = data.get('papers', [])
        if not papers:
            return jsonify({'success': False, 'error': 'No papers provided'}), 400

        for paper in papers:
            title = paper.get('title', '')
            abstract = paper.get('abstract', '')
            # Use advanced extractor for category and keywords
            cat_result = extractor.categorize_paper(title, abstract)
            paper['original_category'] = cat_result.get('original_category', 'Others')
            paper['original_keywords'] = cat_result.get('original_keywords', '')
            # Use advanced extractor for contributions and limitations
            paper['contributions'] = extractor.extract_contributions(abstract)
            paper['limitations'] = extractor.extract_limitations(abstract)
        return jsonify({'success': True, 'papers': papers})
    except Exception as e:
        print(f"[ERROR] Categorization error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/unsupervised_categorize', methods=['POST'])
def unsupervised_categorize():
    """Run unsupervised topic modeling and keyphrase extraction using BERTopic/KeyBERT."""
    try:
        data = request.get_json()
        papers = data.get('papers', [])
        if not papers:
            return jsonify({'success': False, 'error': 'No papers provided'}), 400

        # Save input papers to a temp CSV
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.csv', delete=False) as tmp_in:
            df = pd.DataFrame(papers)
            df.to_csv(tmp_in.name, index=False)
            input_path = tmp_in.name

        # Output path
        output_path = input_path.replace('.csv', '_out.csv')

        # Call the unsupervised script as a subprocess
        script_path = os.path.join(os.path.dirname(__file__), 'unsupervised_category_keyword_extractor.py')
        cmd = [
            'python3', script_path,
            '--input', input_path,
            '--output', output_path
        ]
        # If script does not support --input/--output, just edit script to use input_path/output_path
        try:
            subprocess.run(cmd, check=True)
        except Exception as e:
            # fallback: run without args (script uses hardcoded paths)
            subprocess.run(['python3', script_path], check=True)

        # Read the enhanced CSV
        df_out = pd.read_csv(output_path)
        # Only return the new columns
        new_cols = ['original_category', 'original_keywords', 'contributions', 'limitations']
        result = df_out[new_cols].to_dict(orient='records')
        return jsonify({'success': True, 'papers': result})
    except Exception as e:
        print(f"[ERROR] Unsupervised categorization error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Starting Research Paper Pipeline Server on port 8000")
    app.run(host='0.0.0.0', port=8000, debug=True)

# For Vercel deployment
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size
