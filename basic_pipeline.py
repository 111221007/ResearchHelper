#!/usr/bin/env python3
"""
Basic Research Paper Pipeline API - Minimal Working Version
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import json
import re
import urllib.parse

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return send_from_directory('.', 'index_pipeline.html')

@app.route('/api/fetch', methods=['POST'])
def fetch_papers():
    """Simple paper fetching from CrossRef"""
    try:
        data = request.json
        keyword = data.get('keyword', 'serverless')
        additional_keyword = data.get('additional_keyword', 'performance')
        from_year = data.get('from_year', 2020)
        to_year = data.get('to_year', 2025)
        total_results = min(int(data.get('total_results', 10)), 20)

        print(f"Fetching papers for: {keyword}")

        # Simple CrossRef API call
        url = f'https://api.crossref.org/works?query.title={urllib.parse.quote(keyword)}&filter=from-pub-date:{from_year},until-pub-date:{to_year}&rows={total_results}'

        response = requests.get(url, timeout=30)

        if response.status_code == 200:
            data_response = response.json()
            items = data_response.get('message', {}).get('items', [])

            papers = []
            for i, item in enumerate(items[:total_results]):
                # Extract basic info
                title = ''
                if item.get('title') and len(item['title']) > 0:
                    title = item['title'][0] if isinstance(item['title'], list) else item['title']

                authors = []
                if item.get('author'):
                    for author in item['author']:
                        if author.get('family'):
                            name = author.get('given', '') + ' ' + author['family']
                            authors.append(name.strip())

                paper = {
                    'paper_id': f"paper_{str(i+1).zfill(3)}",
                    'title': title,
                    'abstract': '',
                    'authors': '; '.join(authors) if authors else 'Not Available',
                    'journal': item.get('container-title', [''])[0] if item.get('container-title') else '',
                    'year': str(item.get('published-print', {}).get('date-parts', [['']])[0][0]) if item.get('published-print', {}).get('date-parts') else '',
                    'doi': item.get('DOI', ''),
                    'url': item.get('URL', ''),
                    'type': item.get('type', ''),
                    'volume': item.get('volume', ''),
                    'issue': item.get('issue', ''),
                    'pages': item.get('page', ''),
                    'publisher': item.get('publisher', '')
                }
                papers.append(paper)

            return jsonify({
                'success': True,
                'papers': papers,
                'total': len(papers),
                'message': f'Successfully fetched {len(papers)} papers'
            })
        else:
            return jsonify({'success': False, 'error': f'API request failed: {response.status_code}'}), 500

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/process-complete', methods=['POST'])
def process_complete():
    """Simple processing - just add required fields"""
    try:
        data = request.json
        papers = data.get('papers', [])

        for paper in papers:
            # Add missing fields
            paper['abstract_source'] = 'Not found'
            paper['abstract_confidence'] = 'none'
            paper['original_category'] = 'others'
            paper['original_keywords'] = 'serverless'
            paper['contributions'] = 'Not available'
            paper['limitations'] = 'Not available'

        return jsonify({
            'success': True,
            'papers': papers,
            'message': f'Processed {len(papers)} papers'
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Starting Basic Pipeline Server on port 8000")
    app.run(host='127.0.0.1', port=8000, debug=True)
