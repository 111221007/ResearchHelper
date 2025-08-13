#!/usr/bin/env python3
"""
Research Paper Pipeline API - Original Working Version
Simple and reliable paper fetching and processing
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
    return send_from_directory('.', 'index_pipeline.html')

@app.route('/api/fetch', methods=['POST'])
def fetch_papers():
    """Fetch papers from CrossRef API"""
    try:
        data = request.json
        keyword = data.get('keyword', '').strip()
        additional_keyword = data.get('additional_keyword', '').strip()
        from_year = int(data.get('from_year', 2020))
        to_year = int(data.get('to_year', 2025))
        total_results = min(int(data.get('total_results', 20)), 50)  # Limit to 50
        title_filter = data.get('title_filter', True)
        paper_type_filter = data.get('paper_type_filter', True)

        print(f"Fetching papers: {keyword} + {additional_keyword}, {from_year}-{to_year}, {total_results} results")

        papers = []
        session = get_session()

        # Build CrossRef API URL
        if additional_keyword.strip():
            url = f'https://api.crossref.org/works?query.title={urllib.parse.quote(keyword)}+{urllib.parse.quote(additional_keyword)}'
        else:
            url = f'https://api.crossref.org/works?query.title={urllib.parse.quote(keyword)}'

        url += f'&filter=from-pub-date:{from_year},until-pub-date:{to_year}'
        if paper_type_filter:
            url += ',type:journal-article,type:proceedings-article'
        url += f'&rows={total_results}&sort=relevance'

        response = session.get(url, timeout=30)
        if response.ok:
            data_response = response.json()
            items = data_response.get('message', {}).get('items', [])

            keyword_lower = keyword.lower().strip()
            additional_keyword_lower = additional_keyword.lower().strip()

            count = 0
            for item in items:
                if count >= total_results:
                    break

                # Extract title
                title = ''
                if item.get('title') and len(item['title']) > 0:
                    title = item['title'][0] if isinstance(item['title'], list) else item['title']

                # Title filtering
                if title_filter and title:
                    title_lower = title.lower()
                    keyword_in_title = keyword_lower in title_lower
                    additional_in_title = not additional_keyword_lower or additional_keyword_lower in title_lower

                    if not (keyword_in_title and additional_in_title):
                        continue

                # Extract paper info
                paper = extract_paper_info(item, count + 1)
                papers.append(paper)
                count += 1

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
    # Extract authors
    authors = []
    if item.get('author'):
        for author in item['author']:
            if author.get('given') and author.get('family'):
                authors.append(f"{author['given']} {author['family']}")
            elif author.get('family'):
                authors.append(author['family'])

    # Extract title
    title = ''
    if item.get('title') and len(item['title']) > 0:
        title = item['title'][0] if isinstance(item['title'], list) else item['title']

    # Extract abstract
    abstract = ''
    if item.get('abstract'):
        abstract = re.sub(r'<[^>]+>', '', item['abstract']).replace('\n', ' ').strip()

    # Extract journal
    journal = ''
    if item.get('container-title') and len(item['container-title']) > 0:
        journal = item['container-title'][0] if isinstance(item['container-title'], list) else item['container-title']

    # Extract year
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
                else:
                    # Try arXiv
                    result = search_arxiv(paper.get('title', ''))
                    if result['found']:
                        paper['abstract'] = result['abstract']
                        paper['abstract_source'] = result['source']
                    else:
                        paper['abstract_source'] = 'Not found'
            else:
                paper['abstract_source'] = 'Original'

            # Categorize paper
            categories, keywords = categorize_paper(paper.get('title', ''), paper.get('abstract', ''))
            paper['original_category'] = categories
            paper['original_keywords'] = keywords

            # Simple contributions and limitations
            abstract = paper.get('abstract', '')
            if len(abstract) > 50:
                paper['contributions'] = "Various contributions mentioned in the paper"
                paper['limitations'] = "Limitations discussed in the paper"
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

if __name__ == '__main__':
    print("🚀 Starting Research Paper Pipeline Server on port 8000")
    app.run(host='0.0.0.0', port=8000, debug=True)
