#!/usr/bin/env python3
"""
Enhanced API Server for Multi-Keyword Research Paper Pipeline
Supports multiple keyword configurations and complete processing pipeline
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
from typing import Dict, List

app = Flask(__name__)
CORS(app)

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our pipeline components
try:
    from multi_keyword_fetcher import MultiKeywordPaperFetcher
    from abstract_digger import AbstractDigger
    from enhanced_pdf_downloader import EnhancedPDFDownloader
    from category_keyword_extractor import CategoryKeywordExtractor

    # Initialize components
    pipeline_fetcher = MultiKeywordPaperFetcher()
    abstract_digger = AbstractDigger()
    pdf_downloader = EnhancedPDFDownloader()
    category_extractor = CategoryKeywordExtractor()

    PIPELINE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Pipeline components not available: {e}")
    PIPELINE_AVAILABLE = False

@app.route('/')
def index():
    """Serve the main HTML file"""
    return send_from_directory('.', 'multi_keyword_pipeline.html')

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'pipeline_available': PIPELINE_AVAILABLE
    })

@app.route('/api/fetch-multi-keyword', methods=['POST'])
def fetch_multi_keyword():
    """Fetch papers for multiple keyword configurations"""
    if not PIPELINE_AVAILABLE:
        return jsonify({'error': 'Pipeline components not available'}), 500

    try:
        data = request.get_json()
        keyword_configs = data.get('keyword_configs', [])

        if not keyword_configs:
            return jsonify({'error': 'No keyword configurations provided'}), 400

        # Validate each configuration
        for i, config in enumerate(keyword_configs):
            if not config.get('primary_keyword'):
                return jsonify({'error': f'Configuration {i+1}: Primary keyword is required'}), 400

        # Run multi-keyword fetch
        combined_csv_path = pipeline_fetcher.fetch_multi_keyword_papers(keyword_configs)

        # Read the results
        df = pd.read_csv(combined_csv_path)
        papers = df.to_dict('records')

        return jsonify({
            'status': 'success',
            'message': f'Fetched {len(papers)} unique papers from {len(keyword_configs)} configurations',
            'papers': papers,
            'csv_path': combined_csv_path,
            'statistics': {
                'total_papers': len(papers),
                'configurations_processed': len(keyword_configs)
            }
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/process-complete', methods=['POST'])
def process_complete():
    """Run the complete pipeline: fetch -> abstract -> PDF -> categorize"""
    if not PIPELINE_AVAILABLE:
        return jsonify({'error': 'Pipeline components not available'}), 500

    try:
        data = request.get_json()
        keyword_configs = data.get('keyword_configs', [])

        # Pipeline options
        enable_pdf_download = data.get('enable_pdf_download', True)
        enable_abstract_enhancement = data.get('enable_abstract_enhancement', True)
        enable_categorization = data.get('enable_categorization', True)

        if not keyword_configs:
            return jsonify({'error': 'No keyword configurations provided'}), 400

        print(f"Processing {len(keyword_configs)} keyword configurations")

        # Step 1: Fetch papers
        combined_csv_path = pipeline_fetcher.fetch_multi_keyword_papers(keyword_configs)
        df = pd.read_csv(combined_csv_path)

        stats = {
            'total_configurations': len(keyword_configs),
            'papers_fetched': len(df),
            'papers_after_deduplication': len(df),
            'abstracts_enhanced': 0,
            'pdfs_downloaded': 0,
            'papers_categorized': 0
        }

        current_csv = combined_csv_path

        # Step 2: Abstract enhancement (if enabled)
        if enable_abstract_enhancement:
            print("Starting abstract enhancement...")
            enhanced_df = abstract_digger.process_papers(current_csv)

            # Save enhanced CSV
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            enhanced_csv_name = f"papers_with_abstracts_{timestamp}.csv"
            enhanced_csv_path = os.path.join(abstract_digger.output_dir, enhanced_csv_name)
            enhanced_df.to_csv(enhanced_csv_path, index=False)

            current_csv = enhanced_csv_path
            stats['abstracts_enhanced'] = len(enhanced_df[enhanced_df['abstract_source'] != ''])
            print(f"Abstract enhancement completed: {stats['abstracts_enhanced']} papers enhanced")

        # Step 3: PDF download (if enabled)
        if enable_pdf_download:
            print("Starting PDF downloads...")
            pdf_enhanced_csv = pdf_downloader.download_papers_batch(current_csv, max_workers=2)
            current_csv = pdf_enhanced_csv

            df_with_pdfs = pd.read_csv(current_csv)
            stats['pdfs_downloaded'] = len(df_with_pdfs[df_with_pdfs['pdf_downloaded'] == True])
            print(f"PDF downloads completed: {stats['pdfs_downloaded']} PDFs downloaded")

        # Step 4: Categorization (if enabled)
        if enable_categorization:
            print("Starting categorization...")
            final_csv_path = category_extractor.process_papers_csv(current_csv)
            current_csv = final_csv_path

            df_categorized = pd.read_csv(current_csv)
            stats['papers_categorized'] = len(df_categorized[df_categorized['original_category'] != ''])
            print(f"Categorization completed: {stats['papers_categorized']} papers categorized")

        # Read final results
        final_df = pd.read_csv(current_csv)
        
        # Convert NaN values to empty strings for JSON compatibility
        final_df = final_df.fillna('')
        
        papers = final_df.to_dict('records')
        
        print(f"Pipeline completed successfully: {len(papers)} papers processed")

        return jsonify({
            'status': 'success',
            'message': 'Complete pipeline executed successfully',
            'papers': papers,
            'statistics': stats,
            'final_csv_path': current_csv
        })

    except Exception as e:
        print(f"Pipeline error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Pipeline execution failed: {str(e)}'}), 500

@app.route('/api/download-enhanced-csv', methods=['POST'])
def download_enhanced_csv():
    """Download the final enhanced CSV file"""
    try:
        data = request.get_json()
        papers = data.get('papers', [])

        if not papers:
            return jsonify({'error': 'No papers data provided'}), 400

        # Create DataFrame with all required columns
        df = pd.DataFrame(papers)

        # Ensure all required columns exist
        required_columns = [
            'paper_id', 'title', 'abstract', 'authors', 'journal', 'year', 'volume',
            'issue', 'pages', 'publisher', 'doi', 'url', 'type', 'abstract_source',
            'abstract_confidence', 'original_category', 'original_keywords',
            'contributions', 'limitations'
        ]

        for col in required_columns:
            if col not in df.columns:
                df[col] = ''

        # Reorder columns
        df = df[required_columns]

        # Generate CSV content
        output = io.StringIO()
        df.to_csv(output, index=False)
        csv_content = output.getvalue()

        # Create response
        response = app.response_class(
            csv_content,
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=enhanced_research_papers_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            }
        )

        return response

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-enhanced-bibtex', methods=['POST'])
def generate_enhanced_bibtex():
    """Generate BibTeX from enhanced papers data"""
    try:
        data = request.get_json()
        papers = data.get('papers', [])

        if not papers:
            return jsonify({'error': 'No papers data provided'}), 400

        bibtex_content = ''

        for paper in papers:
            # Determine entry type
            paper_type = paper.get('type', '').lower()
            if 'journal' in paper_type:
                entry_type = 'article'
            elif 'proceedings' in paper_type or 'conference' in paper_type:
                entry_type = 'inproceedings'
            elif 'preprint' in paper_type or 'arxiv' in paper.get('journal', '').lower():
                entry_type = 'misc'
            else:
                entry_type = 'article'

            # Start entry
            bibtex_content += f"@{entry_type}{{{paper.get('paper_id', '')},\n"

            # Add fields
            if paper.get('title'):
                bibtex_content += f"  title={{{paper['title']}}},\n"

            if paper.get('authors'):
                authors = paper['authors'].replace('; ', ' and ')
                bibtex_content += f"  author={{{authors}}},\n"

            if paper.get('journal'):
                if entry_type == 'inproceedings':
                    bibtex_content += f"  booktitle={{{paper['journal']}}},\n"
                else:
                    bibtex_content += f"  journal={{{paper['journal']}}},\n"

            if paper.get('year'):
                bibtex_content += f"  year={{{paper['year']}}},\n"

            if paper.get('volume'):
                bibtex_content += f"  volume={{{paper['volume']}}},\n"

            if paper.get('issue'):
                bibtex_content += f"  number={{{paper['issue']}}},\n"

            if paper.get('pages'):
                bibtex_content += f"  pages={{{paper['pages']}}},\n"

            if paper.get('publisher'):
                bibtex_content += f"  publisher={{{paper['publisher']}}},\n"

            if paper.get('doi'):
                bibtex_content += f"  doi={{{paper['doi']}}},\n"

            if paper.get('url'):
                bibtex_content += f"  url={{{paper['url']}}},\n"

            # Add category as note
            if paper.get('original_category'):
                bibtex_content += f"  note={{Category: {paper['original_category']}}},\n"

            bibtex_content += '}\n\n'

        # Create response
        response = app.response_class(
            bibtex_content,
            mimetype='text/plain',
            headers={
                'Content-Disposition': f'attachment; filename=enhanced_references_{datetime.now().strftime("%Y%m%d_%H%M%S")}.bib'
            }
        )

        return response

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
