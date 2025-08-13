#!/usr/bin/env python3
"""
Research Paper Pipeline API - Restored Working Version with PDF Support
This is the version that was working well before deployment issues
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import pandas as pd
import json
import os
from datetime import datetime
import requests
import time
import re
import random
import urllib.parse
import xml.etree.ElementTree as ET

app = Flask(__name__)
CORS(app)

def get_robust_session():
    """Create a robust requests session with headers"""
    session = requests.Session()
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ]
    session.headers.update({
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    })
    return session

def calculate_title_similarity(title1, title2):
    """Calculate similarity between two titles"""
    if not title1 or not title2:
        return 0.0

    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}

    def clean_title(title):
        return set(re.sub(r'[^\w\s]', ' ', title.lower()).split()) - stop_words

    words1 = clean_title(title1)
    words2 = clean_title(title2)

    if not words1 or not words2:
        return 0.0

    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))

    return intersection / union if union > 0 else 0.0

def search_semantic_scholar_enhanced(title, doi=None):
    """Enhanced Semantic Scholar search with better error handling"""
    try:
        session = get_robust_session()

        if doi and doi.strip():
            search_url = f"https://api.semanticscholar.org/graph/v1/paper/{doi}"
            params = {'fields': 'paperId,title,abstract,authors,journal,year,venue,citationCount,openAccessPdf,url,externalIds'}
        else:
            clean_title = re.sub(r'[^\w\s]', ' ', title).strip()
            search_url = f"https://api.semanticscholar.org/graph/v1/paper/search"
            params = {
                'query': clean_title,
                'fields': 'paperId,title,abstract,authors,journal,year,venue,citationCount,openAccessPdf,url,externalIds',
                'limit': 10
            }

        response = session.get(search_url, params=params, timeout=30)

        if response.status_code == 200:
            data = response.json()

            if doi:
                if data.get('abstract'):
                    return {
                        'found': True,
                        'abstract': data['abstract'],
                        'source': 'Semantic Scholar',
                        'confidence': 'high'
                    }
            else:
                papers = data.get('data', [])
                for paper in papers:
                    if paper.get('abstract'):
                        similarity = calculate_title_similarity(title, paper.get('title', ''))
                        if similarity > 0.7:
                            return {
                                'found': True,
                                'abstract': paper['abstract'],
                                'source': 'Semantic Scholar',
                                'confidence': 'high' if similarity > 0.8 else 'medium'
                            }

        time.sleep(1)

    except Exception as e:
        print(f"Semantic Scholar error for '{title}': {e}")

    return {'found': False, 'abstract': '', 'source': 'Semantic Scholar', 'confidence': 'none'}

def search_arxiv_enhanced(title):
    """Enhanced arXiv search"""
    try:
        session = get_robust_session()
        clean_title = re.sub(r'[^\w\s]', ' ', title).strip()
        search_query = urllib.parse.quote(clean_title)

        url = f"http://export.arxiv.org/api/query?search_query=ti:{search_query}&max_results=10"

        response = session.get(url, timeout=30)
        if response.status_code == 200:
            root = ET.fromstring(response.content)

            for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
                entry_title_elem = entry.find('{http://www.w3.org/2005/Atom}title')
                summary_elem = entry.find('{http://www.w3.org/2005/Atom}summary')

                if entry_title_elem is not None and summary_elem is not None:
                    entry_title = entry_title_elem.text.strip()
                    similarity = calculate_title_similarity(title, entry_title)

                    if similarity > 0.7:
                        summary = summary_elem.text.strip()
                        return {
                            'found': True,
                            'abstract': summary,
                            'source': 'arXiv',
                            'confidence': 'high' if similarity > 0.8 else 'medium'
                        }

        time.sleep(1)

    except Exception as e:
        print(f"arXiv error for '{title}': {e}")

    return {'found': False, 'abstract': '', 'source': 'arXiv', 'confidence': 'none'}

def generate_contributions_limitations(title, abstract):
    """Generate contributions and limitations from title and abstract"""
    if not abstract or len(abstract.strip()) < 50:
        return "Not available due to insufficient abstract content", "Not explicitly mentioned"

    try:
        abstract_lower = abstract.lower()

        contribution_keywords = ['novel', 'new', 'propose', 'introduce', 'develop', 'design', 'implement',
                               'improve', 'enhance', 'advance', 'achieve', 'demonstrate', 'show', 'present']

        limitation_keywords = ['limitation', 'limit', 'constraint', 'challenge', 'future work', 'not',
                             'however', 'but', 'although', 'despite', 'weakness', 'drawback']

        contributions = []
        limitations = []
        sentences = re.split(r'[.!?]', abstract)

        for sentence in sentences:
            sentence_lower = sentence.lower().strip()
            if any(keyword in sentence_lower for keyword in contribution_keywords):
                if len(sentence.strip()) > 20:
                    contributions.append(sentence.strip())

        for sentence in sentences:
            sentence_lower = sentence.lower().strip()
            if any(keyword in sentence_lower for keyword in limitation_keywords):
                if len(sentence.strip()) > 20:
                    limitations.append(sentence.strip())

        contribution_text = '; '.join(contributions[:3]) if contributions else "Various technical contributions mentioned in abstract"
        limitation_text = '; '.join(limitations[:2]) if limitations else "Not explicitly mentioned"

        return contribution_text, limitation_text

    except Exception as e:
        print(f"Error generating contributions/limitations: {e}")
        return "Error in processing", "Error in processing"

def categorize_paper(title, abstract):
    """Categorize paper and extract keywords"""
    try:
        text = f"{title} {abstract}".lower()

        categories = {
            'survey': ['survey', 'review', 'taxonomy', 'systematic review', 'literature review'],
            'latency': ['latency', 'response time', 'cold start', 'warm start', 'startup time'],
            'reliability': ['reliability', 'fault tolerance', 'availability', 'resilience'],
            'security': ['security', 'privacy', 'authentication', 'authorization', 'vulnerability'],
            'privacy': ['privacy', 'data protection', 'confidentiality', 'anonymity'],
            'qos': ['quality of service', 'qos', 'service level', 'performance guarantee'],
            'cost': ['cost', 'pricing', 'billing', 'economic', 'financial'],
            'energy consumption': ['energy', 'power', 'consumption', 'efficiency', 'green'],
            'resource management': ['resource', 'allocation', 'scheduling', 'management', 'provisioning'],
            'benchmark': ['benchmark', 'evaluation', 'comparison', 'measurement', 'testing'],
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

        tech_keywords = ['serverless', 'cloud', 'microservices', 'docker', 'kubernetes',
                        'aws', 'azure', 'google cloud', 'lambda', 'function']

        for keyword in tech_keywords:
            if keyword in text and keyword not in found_keywords:
                found_keywords.append(keyword)

        return ', '.join(found_categories), ', '.join(found_keywords[:10])

    except Exception as e:
        print(f"Error categorizing paper: {e}")
        return 'others', 'serverless'

def fetch_abstract_comprehensive(title, doi=None, url=None):
    """Comprehensive abstract fetching from multiple sources"""
    print(f"Fetching abstract for: {title[:100]}...")

    result = search_semantic_scholar_enhanced(title, doi)
    if result['found'] and result['abstract']:
        return result

    result = search_arxiv_enhanced(title)
    if result['found'] and result['abstract']:
        return result

    return {'found': False, 'abstract': '', 'source': 'None', 'confidence': 'none'}

@app.route('/')
def index():
    return send_from_directory('.', 'index_fixed.html')

@app.route('/api/fetch', methods=['POST'])
def fetch_papers():
    """Fetch papers from CrossRef API"""
    try:
        data = request.json
        keyword = data.get('keyword', '').strip()
        additional_keyword = data.get('additional_keyword', '').strip()
        from_year = int(data.get('from_year', 2020))
        to_year = int(data.get('to_year', 2025))
        total_results = min(int(data.get('total_results', 20)), 100)
        title_filter = data.get('title_filter', True)
        paper_type_filter = data.get('paper_type_filter', True)

        print(f"Fetching papers: {keyword} + {additional_keyword}, {from_year}-{to_year}, {total_results} results")

        papers = []
        session = get_robust_session()

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

                response = session.get(url, timeout=30)
                if not response.ok:
                    break

                data_response = response.json()
                items = data_response.get('message', {}).get('items', [])

                if not items:
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
                print(f"Error fetching batch: {e}")
                break

        return jsonify({
            'success': True,
            'papers': papers,
            'total': len(papers),
            'message': f'Successfully fetched {len(papers)} papers'
        })

    except Exception as e:
        print(f"Fetch error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

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

@app.route('/api/process-complete', methods=['POST'])
def process_complete_pipeline():
    """Process the complete pipeline: deduplicate, extract abstracts, categorize"""
    try:
        data = request.json
        papers = data.get('papers', [])

        if not papers:
            return jsonify({'success': False, 'error': 'No papers provided'}), 400

        print(f"Processing {len(papers)} papers through complete pipeline...")

        deduplicated_papers = deduplicate_papers(papers)

        papers_with_abstracts = []

        for i, paper in enumerate(deduplicated_papers):
            print(f"Processing paper {i+1}/{len(deduplicated_papers)}: {paper.get('title', '')[:50]}...")

            if not paper.get('abstract') or len(paper['abstract'].strip()) < 50:
                abstract_result = fetch_abstract_comprehensive(
                    paper.get('title', ''),
                    paper.get('doi', ''),
                    paper.get('url', '')
                )

                if abstract_result['found']:
                    paper['abstract'] = abstract_result['abstract']
                    paper['abstract_source'] = abstract_result['source']
                    paper['abstract_confidence'] = abstract_result['confidence']
                else:
                    paper['abstract_source'] = 'Not found'
                    paper['abstract_confidence'] = 'none'
            else:
                paper['abstract_source'] = 'Original'
                paper['abstract_confidence'] = 'high'

            categories, keywords = categorize_paper(paper.get('title', ''), paper.get('abstract', ''))
            paper['original_category'] = categories
            paper['original_keywords'] = keywords

            contributions, limitations = generate_contributions_limitations(
                paper.get('title', ''), paper.get('abstract', '')
            )
            paper['contributions'] = contributions
            paper['limitations'] = limitations

            papers_with_abstracts.append(paper)
            time.sleep(0.1)

        return jsonify({
            'success': True,
            'papers': papers_with_abstracts,
            'original_count': len(papers),
            'deduplicated_count': len(deduplicated_papers),
            'processed_count': len(papers_with_abstracts),
            'message': f'Successfully processed {len(papers_with_abstracts)} papers'
        })

    except Exception as e:
        print(f"Processing error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def deduplicate_papers(papers):
    """Remove duplicate papers based on title similarity and DOI"""
    if not papers:
        return []

    unique_papers = []
    seen_dois = set()
    seen_titles = []

    for paper in papers:
        doi = paper.get('doi', '').strip()
        if doi and doi in seen_dois:
            continue
        if doi:
            seen_dois.add(doi)

        title = paper.get('title', '').strip()
        is_duplicate = False

        for seen_title in seen_titles:
            if calculate_title_similarity(title, seen_title) > 0.85:
                is_duplicate = True
                break

        if not is_duplicate:
            seen_titles.append(title)
            unique_papers.append(paper)

    return unique_papers

@app.route('/api/download-pdfs', methods=['POST'])
def download_pdfs():
    """Simple PDF download functionality"""
    try:
        data = request.json
        papers = data.get('papers', [])

        if not papers:
            return jsonify({'success': False, 'error': 'No papers provided'}), 400

        print(f"Starting PDF download for {len(papers)} papers...")

        # Create results directory for PDFs
        pdf_dir = "/Users/reddy/2025/ResearchHelper/results/pdf"
        os.makedirs(pdf_dir, exist_ok=True)

        downloaded_count = 0
        results = []
        session = get_robust_session()

        for i, paper in enumerate(papers):
            paper_id = paper.get('paper_id', f'paper_{i+1:03d}')
            title = paper.get('title', f'Paper {i+1}')
            print(f"Processing paper {i+1}/{len(papers)}: {title[:50]}...")

            pdf_downloaded = False
            download_source = "None"

            try:
                # Method 1: Check if URL is arXiv paper
                url = paper.get('url', '')
                if 'arxiv.org' in url:
                    arxiv_match = re.search(r'arxiv\.org/(?:abs|pdf)/([^/\s]+)', url)
                    if arxiv_match:
                        arxiv_id = arxiv_match.group(1).replace('.pdf', '')
                        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

                        try:
                            response = session.get(pdf_url, timeout=30, stream=True)
                            if response.status_code == 200:
                                # Create safe filename
                                safe_title = re.sub(r'[^\w\s-]', '', title)[:30]
                                filename = f"{paper_id}_{safe_title}.pdf".replace(' ', '_')
                                filepath = os.path.join(pdf_dir, filename)

                                with open(filepath, 'wb') as f:
                                    for chunk in response.iter_content(chunk_size=8192):
                                        if chunk:
                                            f.write(chunk)

                                # Verify it's a valid PDF
                                if os.path.getsize(filepath) > 1000:
                                    with open(filepath, 'rb') as f:
                                        header = f.read(8)
                                        if header.startswith(b'%PDF-'):
                                            downloaded_count += 1
                                            pdf_downloaded = True
                                            download_source = pdf_url
                                            print(f"✅ Downloaded: {filename}")
                                        else:
                                            os.remove(filepath)
                                else:
                                    if os.path.exists(filepath):
                                        os.remove(filepath)
                        except Exception as e:
                            print(f"❌ arXiv download failed: {e}")

                # Method 2: Try Semantic Scholar for open access PDFs
                if not pdf_downloaded:
                    try:
                        ss_url = f"https://api.semanticscholar.org/graph/v1/paper/search"
                        params = {'query': title, 'limit': 1, 'fields': 'openAccessPdf'}
                        response = session.get(ss_url, params=params, timeout=10)

                        if response.status_code == 200:
                            data_ss = response.json()
                            papers_ss = data_ss.get('data', [])

                            if papers_ss and papers_ss[0].get('openAccessPdf'):
                                pdf_url = papers_ss[0]['openAccessPdf'].get('url')
                                if pdf_url:
                                    try:
                                        response = session.get(pdf_url, timeout=30, stream=True)
                                        if response.status_code == 200:
                                            safe_title = re.sub(r'[^\w\s-]', '', title)[:30]
                                            filename = f"{paper_id}_{safe_title}.pdf".replace(' ', '_')
                                            filepath = os.path.join(pdf_dir, filename)

                                            with open(filepath, 'wb') as f:
                                                for chunk in response.iter_content(chunk_size=8192):
                                                    if chunk:
                                                        f.write(chunk)

                                            if os.path.getsize(filepath) > 1000:
                                                with open(filepath, 'rb') as f:
                                                    header = f.read(8)
                                                    if header.startswith(b'%PDF-'):
                                                        downloaded_count += 1
                                                        pdf_downloaded = True
                                                        download_source = pdf_url
                                                        print(f"✅ Downloaded: {filename}")
                                                    else:
                                                        os.remove(filepath)
                                            else:
                                                if os.path.exists(filepath):
                                                    os.remove(filepath)
                                    except Exception as e:
                                        print(f"❌ Semantic Scholar download failed: {e}")

                        time.sleep(0.5)  # Rate limiting
                    except Exception as e:
                        print(f"❌ Semantic Scholar API error: {e}")

            except Exception as e:
                print(f"❌ Error processing paper {paper_id}: {e}")

            results.append({
                'paper_id': paper_id,
                'title': title,
                'pdf_downloaded': pdf_downloaded,
                'download_source': download_source
            })

            if not pdf_downloaded:
                print(f"❌ No PDF found for: {title[:50]}")

        summary = {
            'total_papers': len(papers),
            'pdfs_found': downloaded_count,
            'download_success_rate': f"{(downloaded_count/len(papers)*100):.1f}%" if papers else "0%",
            'results': results
        }

        print(f"\n📊 DOWNLOAD SUMMARY:")
        print(f"Total papers processed: {len(papers)}")
        print(f"PDFs successfully downloaded: {downloaded_count}")
        print(f"Success rate: {(downloaded_count/len(papers)*100):.1f}%")
        print(f"PDFs saved to: {pdf_dir}")

        return jsonify({
            'success': True,
            'summary': summary,
            'pdf_directory': pdf_dir
        })

    except Exception as e:
        print(f"❌ PDF download error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Starting Research Paper Pipeline Server on port 8000")
    app.run(host='0.0.0.0', port=8000, debug=True)
