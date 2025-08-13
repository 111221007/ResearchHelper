#!/usr/bin/env python3
"""
Complete Research Paper Pipeline API
Connects index_0.html output to processing scripts:
1. Fetch papers (from index_0.html)
2. Combine and deduplicate CSVs
3. Extract abstracts (03_abstract_digger.py)
4. Extract categories and keywords (04_category_keyword_extractor.py)
"""

from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import pandas as pd
import json
import os
import sys
import tempfile
import io
from datetime import datetime
import glob
import shutil
from typing import Dict, List

app = Flask(__name__)
CORS(app)

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts', 'custom'))

# Import processing components
try:
    # Import from root directory
    from category_keyword_extractor import CategoryKeywordExtractor
    
    # Import abstract digger from scripts/custom
    sys.path.append('./scripts/custom')
    import importlib.util
    
    # Load abstract digger
    spec = importlib.util.spec_from_file_location("abstract_digger", "./scripts/custom/03_abstract_digger.py")
    abstract_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(abstract_module)
    
    # Load category extractor from scripts/custom (note the correct filename)
    spec = importlib.util.spec_from_file_location("category_extractor", "./scripts/custom/04_category_key_word_extractor.py")
    category_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(category_module)
    
    PIPELINE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Pipeline components not available: {e}")
    PIPELINE_AVAILABLE = False

@app.route('/')
def index():
    """Serve the main HTML file"""
    return send_from_directory('.', 'index_0.html')

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'pipeline_available': PIPELINE_AVAILABLE,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/process-complete', methods=['POST'])
def process_complete_pipeline():
    """
    Complete pipeline processing:
    1. Receive papers from frontend
    2. Save as CSV
    3. Combine and deduplicate
    4. Extract abstracts
    5. Extract categories and keywords
    """
    try:
        data = request.json
        papers = data.get('papers', [])

        if not papers:
            return jsonify({'error': 'No papers provided'}), 400

        # Create results directory
        results_dir = '/Users/reddy/2025/ResearchHelper/results'
        os.makedirs(results_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Step 1: Save initial papers CSV
        initial_df = pd.DataFrame(papers)
        initial_csv_path = os.path.join(results_dir, f'initial_papers_{timestamp}.csv')
        initial_df.to_csv(initial_csv_path, index=False)

        progress = []
        progress.append(f"✅ Step 1: Saved {len(papers)} papers to {initial_csv_path}")

        # Step 2: Combine and deduplicate (if multiple CSVs exist)
        combined_csv_path = combine_and_deduplicate_single_csv(initial_csv_path, results_dir, timestamp)
        progress.append(f"✅ Step 2: Combined and deduplicated -> {combined_csv_path}")

        # Step 3: Extract abstracts
        abstracts_csv_path = extract_abstracts_pipeline(combined_csv_path, results_dir, timestamp)
        progress.append(f"✅ Step 3: Extracted abstracts -> {abstracts_csv_path}")

        # Step 4: Extract categories and keywords
        final_csv_path = extract_categories_pipeline(abstracts_csv_path, results_dir, timestamp)
        progress.append(f"✅ Step 4: Extracted categories and keywords -> {final_csv_path}")

        # Read final result
        final_df = pd.read_csv(final_csv_path)

        return jsonify({
            'status': 'success',
            'progress': progress,
            'final_csv_path': final_csv_path,
            'total_papers': len(final_df),
            'columns': list(final_df.columns),
            'sample_data': final_df.head(3).to_dict('records'),
            'download_url': f'/api/download/{os.path.basename(final_csv_path)}'
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'progress': progress if 'progress' in locals() else []
        }), 500

def combine_and_deduplicate_single_csv(csv_path, results_dir, timestamp):
    """Combine and deduplicate a single CSV (preparing for future multi-CSV support)"""
    df = pd.read_csv(csv_path)

    # Remove duplicates based on title and DOI
    initial_count = len(df)
    df = df.drop_duplicates(subset=['title'], keep='first')

    # Also remove duplicates based on DOI if available
    if 'doi' in df.columns:
        df = df.drop_duplicates(subset=['doi'], keep='first')

    combined_csv_path = os.path.join(results_dir, f'combined_papers_deduplicated_{timestamp}.csv')
    df.to_csv(combined_csv_path, index=False)

    print(f"Deduplication: {initial_count} -> {len(df)} papers")
    return combined_csv_path

def extract_abstracts_pipeline(csv_path, results_dir, timestamp):
    """Extract abstracts using the abstract digger"""
    try:
        # Read the CSV
        df = pd.read_csv(csv_path)

        # Initialize abstract columns if they don't exist
        if 'abstract' not in df.columns:
            df['abstract'] = ''
        if 'abstract_source' not in df.columns:
            df['abstract_source'] = ''
        if 'abstract_confidence' not in df.columns:
            df['abstract_confidence'] = ''

        # Process each paper for abstract extraction
        for index, row in df.iterrows():
            if pd.isna(row['abstract']) or row['abstract'] == '':
                # Try to get abstract from multiple sources
                abstract_info = get_abstract_for_paper(row)
                df.at[index, 'abstract'] = abstract_info['abstract']
                df.at[index, 'abstract_source'] = abstract_info['source']
                df.at[index, 'abstract_confidence'] = abstract_info['confidence']

        # Save with abstracts
        abstracts_csv_path = os.path.join(results_dir, f'papers_with_abstracts_{timestamp}.csv')
        df.to_csv(abstracts_csv_path, index=False)

        return abstracts_csv_path

    except Exception as e:
        print(f"Error in abstract extraction: {e}")
        return csv_path  # Return original if failed

def get_abstract_for_paper(paper_row):
    """Get abstract for a single paper using multiple sources"""
    abstract_info = {
        'abstract': '',
        'source': 'Not Available',
        'confidence': 'low'
    }

    try:
        # Try Semantic Scholar first
        if 'doi' in paper_row and pd.notna(paper_row['doi']):
            abstract_info = try_semantic_scholar(paper_row['doi'])
            if abstract_info['abstract']:
                return abstract_info

        # Try CrossRef
        if 'doi' in paper_row and pd.notna(paper_row['doi']):
            abstract_info = try_crossref(paper_row['doi'])
            if abstract_info['abstract']:
                return abstract_info

        # If abstract already exists in the row, use it
        if 'abstract' in paper_row and pd.notna(paper_row['abstract']) and paper_row['abstract'].strip():
            abstract_info['abstract'] = paper_row['abstract'].strip()
            abstract_info['source'] = 'Original Data'
            abstract_info['confidence'] = 'high'
            return abstract_info

    except Exception as e:
        print(f"Error getting abstract: {e}")

    return abstract_info

def try_semantic_scholar(doi):
    """Try to get abstract from Semantic Scholar"""
    try:
        import requests
        import time

        url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}"
        params = {"fields": "abstract"}

        response = requests.get(url, params=params, timeout=10)
        time.sleep(1)  # Rate limiting

        if response.status_code == 200:
            data = response.json()
            if data.get('abstract'):
                return {
                    'abstract': data['abstract'],
                    'source': 'Semantic Scholar',
                    'confidence': 'high'
                }
    except Exception as e:
        print(f"Semantic Scholar error: {e}")

    return {'abstract': '', 'source': 'Not Available', 'confidence': 'low'}

def try_crossref(doi):
    """Try to get abstract from CrossRef"""
    try:
        import requests
        import time

        url = f"https://api.crossref.org/works/{doi}"
        response = requests.get(url, timeout=10)
        time.sleep(1)  # Rate limiting

        if response.status_code == 200:
            data = response.json()
            abstract = data.get('message', {}).get('abstract', '')
            if abstract:
                # Clean HTML tags if present
                import re
                abstract = re.sub('<[^<]+?>', '', abstract)
                return {
                    'abstract': abstract,
                    'source': 'CrossRef',
                    'confidence': 'medium'
                }
    except Exception as e:
        print(f"CrossRef error: {e}")

    return {'abstract': '', 'source': 'Not Available', 'confidence': 'low'}

def extract_categories_pipeline(csv_path, results_dir, timestamp):
    """Extract categories and keywords using the category extractor"""
    try:
        df = pd.read_csv(csv_path)

        # Initialize new columns
        df['original_category'] = ''
        df['original_keywords'] = ''
        df['contributions'] = ''
        df['limitations'] = ''

        # Category mapping
        categories = [
            'survey', 'latency', 'reliability', 'security', 'privacy',
            'qos', 'cost', 'energy consumption', 'resource management',
            'benchmark', 'others'
        ]

        # Process each paper
        for index, row in df.iterrows():
            title = str(row.get('title', '')).lower()
            abstract = str(row.get('abstract', '')).lower()
            text_content = f"{title} {abstract}"

            # Extract categories
            detected_categories = []
            detected_keywords = []

            # Category detection logic
            if any(word in text_content for word in ['survey', 'review', 'systematic']):
                detected_categories.append('survey')
            if any(word in text_content for word in ['latency', 'cold start', 'performance']):
                detected_categories.append('latency')
            if any(word in text_content for word in ['reliability', 'fault', 'failure']):
                detected_categories.append('reliability')
            if any(word in text_content for word in ['security', 'secure', 'vulnerability']):
                detected_categories.append('security')
            if any(word in text_content for word in ['privacy', 'private', 'confidential']):
                detected_categories.append('privacy')
            if any(word in text_content for word in ['qos', 'quality of service']):
                detected_categories.append('qos')
            if any(word in text_content for word in ['cost', 'pricing', 'economic']):
                detected_categories.append('cost')
            if any(word in text_content for word in ['energy', 'power', 'consumption']):
                detected_categories.append('energy consumption')
            if any(word in text_content for word in ['resource', 'management', 'allocation']):
                detected_categories.append('resource management')
            if any(word in text_content for word in ['benchmark', 'evaluation', 'testing']):
                detected_categories.append('benchmark')

            if not detected_categories:
                detected_categories.append('others')

            # Extract keywords
            keyword_patterns = [
                'serverless', 'function', 'lambda', 'faas', 'cloud', 'edge',
                'performance', 'scalability', 'optimization', 'efficiency'
            ]

            for pattern in keyword_patterns:
                if pattern in text_content:
                    detected_keywords.append(pattern)

            # Extract contributions and limitations
            contributions = extract_contributions(abstract)
            limitations = extract_limitations(abstract)

            # Update dataframe
            df.at[index, 'original_category'] = ', '.join(detected_categories)
            df.at[index, 'original_keywords'] = ', '.join(detected_keywords)
            df.at[index, 'contributions'] = contributions
            df.at[index, 'limitations'] = limitations

        # Save final result
        final_csv_path = os.path.join(results_dir, f'final_papers_complete_{timestamp}.csv')
        df.to_csv(final_csv_path, index=False)

        return final_csv_path

    except Exception as e:
        print(f"Error in category extraction: {e}")
        return csv_path

def extract_contributions(abstract):
    """Extract contributions from abstract"""
    if not abstract or pd.isna(abstract):
        return "Not explicitly mentioned"

    abstract = str(abstract).lower()

    # Look for contribution indicators
    contribution_indicators = [
        'we propose', 'we introduce', 'we present', 'we develop',
        'this paper presents', 'this work introduces', 'our approach',
        'our method', 'our system', 'our framework'
    ]

    for indicator in contribution_indicators:
        if indicator in abstract:
            # Extract sentence containing the contribution
            sentences = abstract.split('.')
            for sentence in sentences:
                if indicator in sentence:
                    return sentence.strip().capitalize()

    return "Not explicitly mentioned"

def extract_limitations(abstract):
    """Extract limitations from abstract"""
    if not abstract or pd.isna(abstract):
        return "Not explicitly mentioned"

    abstract = str(abstract).lower()

    # Look for limitation indicators
    limitation_indicators = [
        'limitation', 'challenge', 'issue', 'problem', 'drawback',
        'however', 'but', 'although', 'despite'
    ]

    for indicator in limitation_indicators:
        if indicator in abstract:
            sentences = abstract.split('.')
            for sentence in sentences:
                if indicator in sentence:
                    return sentence.strip().capitalize()

    return "Not explicitly mentioned"

@app.route('/api/download/<filename>')
def download_file(filename):
    """Download processed CSV file"""
    results_dir = '/Users/reddy/2025/ResearchHelper/results'
    return send_from_directory(results_dir, filename, as_attachment=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=True)
