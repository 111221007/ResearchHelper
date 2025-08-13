#!/usr/bin/env python3
"""
Simplified Research Paper Pipeline API for Vercel
Lightweight version without heavy data science dependencies
"""

from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS
import requests
import time
import re
import urllib.parse
import json
import tempfile
import os

app = Flask(__name__)
CORS(app)

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

        time.sleep(1)
    except Exception as e:
        print(f"Semantic Scholar error: {e}")

    return {'found': False, 'abstract': '', 'source': 'Semantic Scholar'}

def categorize_paper_simple(title, abstract):
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

def extract_contributions_simple(abstract):
    """Simple contributions extraction"""
    if not abstract:
        return "Not available"

    text = abstract.lower()
    if any(word in text for word in ['propose', 'present', 'introduce', 'develop', 'design']):
        return "Novel approach and methodology presented"
    return "Various contributions mentioned in the paper"

def extract_limitations_simple(abstract):
    """Simple limitations extraction"""
    if not abstract:
        return "Not available"

    text = abstract.lower()
    if any(word in text for word in ['limitation', 'challenge', 'future work', 'improve']):
        return "Limitations and future work discussed"
    return "Not explicitly mentioned"

@app.route('/')
def index():
    """Serve the main page"""
    try:
        with open('index.html', 'r') as f:
            return f.read()
    except:
        return jsonify({"message": "Research Paper Pipeline API", "status": "running"})

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
        print(f"Error in fetch_papers: {e}")
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

@app.route('/api/process-complete', methods=['POST'])
def process_complete():
    """Process papers: deduplicate, extract abstracts, categorize"""
    try:
        data = request.json
        papers = data.get('papers', [])

        if not papers:
            return jsonify({'success': False, 'error': 'No papers provided'}), 400

        # Simple deduplication
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
            # Extract abstract if not available
            if not paper.get('abstract') or len(paper['abstract'].strip()) < 50:
                result = search_semantic_scholar(paper.get('title', ''))
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
            categories, keywords = categorize_paper_simple(paper.get('title', ''), paper.get('abstract', ''))
            paper['original_category'] = categories
            paper['original_keywords'] = keywords

            # Extract contributions and limitations
            paper['contributions'] = extract_contributions_simple(paper.get('abstract', ''))
            paper['limitations'] = extract_limitations_simple(paper.get('abstract', ''))

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

@app.route('/api/download-csv', methods=['POST'])
def download_csv():
    """Generate and download CSV file"""
    try:
        data = request.json
        papers = data.get('papers', [])

        if not papers:
            return jsonify({'success': False, 'error': 'No papers provided'}), 400

        # Generate CSV content
        headers = ['paper_id', 'title', 'abstract', 'authors', 'journal', 'year', 'volume', 'issue', 'pages', 'publisher', 'doi', 'url', 'type', 'abstract_source', 'abstract_confidence', 'original_category', 'original_keywords', 'contributions', 'limitations']

        csv_content = ','.join(headers) + '\n'

        for paper in papers:
            row = []
            for header in headers:
                value = str(paper.get(header, ''))
                # Escape quotes and wrap in quotes if contains comma
                if ',' in value or '"' in value or '\n' in value:
                    value = '"' + value.replace('"', '""') + '"'
                row.append(value)
            csv_content += ','.join(row) + '\n'

        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        temp_file.write(csv_content)
        temp_file.close()

        return send_file(temp_file.name, as_attachment=True, download_name='research_papers.csv', mimetype='text/csv')

    except Exception as e:
        print(f"CSV download error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
