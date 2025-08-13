#!/usr/bin/env python3
"""
Research Paper Fetcher Web GUI with To Year Feature
A web-based interface for fetching research papers using Crossref API
with directory opening functionality after fetching.
"""

import pandas as pd
import requests
import time
import os
import subprocess
import webbrowser
from typing import List, Dict, Optional
from urllib.parse import quote
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import threading
import urllib.parse


class PaperFetcherHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the paper fetcher web interface"""

    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/':
            self.serve_main_page()
        elif self.path == '/api/status':
            self.serve_status()
        elif self.path.startswith('/api/fetch'):
            self.handle_fetch_request()
        elif self.path == '/api/open-folder':
            self.handle_open_folder()
        else:
            self.send_error(404)

    def do_POST(self):
        """Handle POST requests"""
        if self.path == '/api/fetch':
            self.handle_fetch_request()
        else:
            self.send_error(404)

    def serve_main_page(self):
        """Serve the main HTML page"""
        html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔬 Research Paper Fetcher</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(45deg, #4f46e5, #7c3aed);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 700;
        }
        
        .header p {
            font-size: 1.1em;
            opacity: 0.9;
        }
        
        .form-container {
            padding: 40px;
        }
        
        .form-group {
            margin-bottom: 25px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #374151;
            font-size: 1.1em;
        }
        
        .form-group input[type="text"], .form-group input[type="number"] {
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #e5e7eb;
            border-radius: 8px;
            font-size: 1em;
            transition: border-color 0.3s ease;
        }
        
        .form-group input:focus {
            outline: none;
            border-color: #4f46e5;
            box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
        }
        
        .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        
        .checkbox-group {
            background: #f9fafb;
            padding: 20px;
            border-radius: 8px;
            border: 2px solid #e5e7eb;
        }
        
        .checkbox-group h3 {
            margin-bottom: 15px;
            color: #374151;
            font-size: 1.2em;
        }
        
        .checkbox-item {
            display: flex;
            align-items: center;
            margin-bottom: 10px;
        }
        
        .checkbox-item input[type="checkbox"] {
            margin-right: 10px;
            width: 18px;
            height: 18px;
            accent-color: #4f46e5;
        }
        
        .checkbox-item label {
            margin-bottom: 0;
            font-weight: 500;
            color: #4b5563;
        }
        
        .button-group {
            display: flex;
            gap: 15px;
            margin: 30px 0;
        }
        
        .btn {
            padding: 12px 25px;
            border: none;
            border-radius: 8px;
            font-size: 1.1em;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .btn-primary {
            background: linear-gradient(45deg, #4f46e5, #7c3aed);
            color: white;
        }
        
        .btn-primary:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(79, 70, 229, 0.3);
        }
        
        .btn-secondary {
            background: #10b981;
            color: white;
        }
        
        .btn-secondary:hover:not(:disabled) {
            background: #059669;
            transform: translateY(-2px);
        }
        
        .btn-outline {
            background: transparent;
            border: 2px solid #e5e7eb;
            color: #6b7280;
        }
        
        .btn-outline:hover {
            background: #f3f4f6;
        }
        
        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        
        .progress-container {
            margin: 20px 0;
            display: none;
        }
        
        .progress-bar {
            width: 100%;
            height: 8px;
            background: #e5e7eb;
            border-radius: 4px;
            overflow: hidden;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(45deg, #4f46e5, #7c3aed);
            border-radius: 4px;
            animation: progress 2s ease-in-out infinite;
        }
        
        @keyframes progress {
            0% { width: 0%; }
            50% { width: 70%; }
            100% { width: 100%; }
        }
        
        .status {
            margin: 15px 0;
            padding: 15px;
            border-radius: 8px;
            font-weight: 500;
            display: none;
        }
        
        .status.info {
            background: #dbeafe;
            color: #1e40af;
            border: 1px solid #3b82f6;
        }
        
        .status.success {
            background: #d1fae5;
            color: #065f46;
            border: 1px solid #10b981;
        }
        
        .status.error {
            background: #fee2e2;
            color: #991b1b;
            border: 1px solid #ef4444;
        }
        
        .results-container {
            margin-top: 30px;
            display: none;
        }
        
        .results-box {
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 20px;
            max-height: 400px;
            overflow-y: auto;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 0.9em;
            line-height: 1.5;
        }
        
        .example-hint {
            background: #f0f9ff;
            border: 1px solid #0ea5e9;
            border-radius: 6px;
            padding: 15px;
            margin: 20px 0;
        }
        
        .example-hint h4 {
            color: #0c4a6e;
            margin-bottom: 8px;
        }
        
        .example-hint p {
            color: #0369a1;
            margin-bottom: 5px;
        }
        
        .spinner {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(255,255,255,.3);
            border-radius: 50%;
            border-top-color: #fff;
            animation: spin 1s ease-in-out infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔬 Research Paper Fetcher</h1>
            <p>Find and download research papers from Crossref API with advanced filtering</p>
        </div>
        
        <div class="form-container">
            <form id="fetchForm">
                <div class="form-group">
                    <label for="keyword">🔍 Primary Keyword *</label>
                    <input type="text" id="keyword" name="keyword" placeholder="e.g., serverless, machine learning, blockchain" value="serverless" required>
                </div>
                
                <div class="form-group">
                    <label for="additional_keyword">➕ Additional Keyword (optional)</label>
                    <input type="text" id="additional_keyword" name="additional_keyword" placeholder="e.g., performance, security, optimization" value="performance">
                </div>
                
                <div class="form-row">
                    <div class="form-group">
                        <label for="from_year">📅 From Year</label>
                        <input type="number" id="from_year" name="from_year" min="1900" max="2030" value="2020" required>
                    </div>
                    
                    <div class="form-group">
                        <label for="to_year">📅 To Year</label>
                        <input type="number" id="to_year" name="to_year" min="1900" max="2030" value="2025" required>
                    </div>
                </div>
                
                <div class="form-row">
                    <div class="form-group">
                        <label for="total_results">📊 Number of Results</label>
                        <input type="number" id="total_results" name="total_results" min="1" max="1000" value="20" required>
                    </div>
                    
                    <div class="form-group">
                        <!-- Empty space for symmetry -->
                    </div>
                </div>
                
                <div class="form-group">
                    <div class="checkbox-group">
                        <h3>⚙️ Search Options</h3>
                        <div class="checkbox-item">
                            <input type="checkbox" id="title_filter" name="title_filter" checked>
                            <label for="title_filter">Both keywords must appear in title</label>
                        </div>
                        <div class="checkbox-item">
                            <input type="checkbox" id="paper_type_filter" name="paper_type_filter" checked>
                            <label for="paper_type_filter">Journal and Conference papers only</label>
                        </div>
                    </div>
                </div>
                
                <div class="example-hint">
                    <h4>💡 Example Searches:</h4>
                    <p><strong>Serverless + Performance (2020-2025):</strong> Find recent papers about serverless computing performance</p>
                    <p><strong>Machine Learning + Security (2022-2025):</strong> Find latest ML security-related papers</p>
                    <p><strong>Blockchain + Scalability (2021-2024):</strong> Find blockchain scalability research in specific timeframe</p>
                </div>
                
                <div class="button-group">
                    <button type="submit" class="btn btn-primary" id="fetchBtn">
                        <span id="fetchBtnText">🚀 Fetch Papers</span>
                        <span id="fetchSpinner" class="spinner" style="display: none;"></span>
                    </button>
                    <button type="button" class="btn btn-secondary" id="openFolderBtn" disabled>
                        📁 Open Results Folder
                    </button>
                    <button type="button" class="btn btn-outline" id="clearBtn">
                        🗑️ Clear Results
                    </button>
                </div>
                
                <div class="progress-container" id="progressContainer">
                    <div class="progress-bar">
                        <div class="progress-fill"></div>
                    </div>
                </div>
                
                <div class="status" id="statusMessage"></div>
                
                <div class="results-container" id="resultsContainer">
                    <h3>📄 Fetch Results</h3>
                    <div class="results-box" id="resultsBox"></div>
                </div>
            </form>
        </div>
    </div>

    <script>
        let isLoading = false;
        let lastResultFile = '';

        document.getElementById('fetchForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            if (isLoading) return;
            
            // Validate year range
            const fromYear = parseInt(document.getElementById('from_year').value);
            const toYear = parseInt(document.getElementById('to_year').value);
            
            if (fromYear > toYear) {
                alert('From Year cannot be greater than To Year');
                return;
            }
            
            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData.entries());
            
            // Convert checkboxes to boolean
            data.title_filter = document.getElementById('title_filter').checked;
            data.paper_type_filter = document.getElementById('paper_type_filter').checked;
            
            await fetchPapers(data);
        });

        document.getElementById('openFolderBtn').addEventListener('click', async function() {
            if (lastResultFile) {
                try {
                    const response = await fetch('/api/open-folder', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({file: lastResultFile})
                    });
                    const result = await response.json();
                    
                    if (result.success) {
                        addResultMessage('📁 Opened results folder successfully!', 'success');
                    } else {
                        addResultMessage('❌ Failed to open folder: ' + result.error, 'error');
                    }
                } catch (error) {
                    addResultMessage('❌ Error opening folder: ' + error.message, 'error');
                }
            }
        });

        document.getElementById('clearBtn').addEventListener('click', function() {
            document.getElementById('resultsBox').innerHTML = '';
            document.getElementById('resultsContainer').style.display = 'none';
            document.getElementById('statusMessage').style.display = 'none';
            document.getElementById('openFolderBtn').disabled = true;
            lastResultFile = '';
            showStatus('Cleared. Ready to fetch papers...', 'info');
        });

        async function fetchPapers(data) {
            setLoading(true);
            clearResults();
            showProgress();
            showStatus('🔍  Papers fetching... Please wait', 'info');
            
            try {
                const response = await fetch('/api/fetch', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                
                while (true) {
                    const { value, done } = await reader.read();
                    if (done) break;
                    
                    const chunk = decoder.decode(value);
                    const lines = chunk.split('\\n');
                    
                    for (const line of lines) {
                        if (line.trim().startsWith('data: ')) {
                            try {
                                const eventData = JSON.parse(line.substring(6));
                                handleStreamEvent(eventData);
                            } catch (e) {
                                console.error('Error parsing event data:', e);
                            }
                        }
                    }
                }
                
            } catch (error) {
                addResultMessage('❌ Error occurred: ' + error.message, 'error');
                showStatus('Error occurred during fetch', 'error');
            } finally {
                setLoading(false);
                hideProgress();
            }
        }

        function handleStreamEvent(data) {
            if (data.type === 'log') {
                addResultMessage(data.message, data.level || 'info');
            } else if (data.type === 'status') {
                showStatus(data.message, data.level || 'info');
            } else if (data.type === 'complete') {
                lastResultFile = data.file;
                document.getElementById('openFolderBtn').disabled = false;
                showStatus(`✅ Completed! Found ${data.count} papers.`, 'success');
                addResultMessage(`\\n💾 Results saved to: ${data.file}`, 'success');
                // Hide progress and spinner on completion
                setLoading(false);
                hideProgress();
            } else if (data.type === 'error') {
                showStatus('❌ Error occurred during fetch', 'error');
                addResultMessage('❌ ' + data.message, 'error');
                // Hide progress and spinner on error
                setLoading(false);
                hideProgress();
            }
        }

        function setLoading(loading) {
            isLoading = loading;
            const fetchBtn = document.getElementById('fetchBtn');
            const fetchBtnText = document.getElementById('fetchBtnText');
            const fetchSpinner = document.getElementById('fetchSpinner');
            
            fetchBtn.disabled = loading;
            fetchBtnText.style.display = loading ? 'none' : 'inline';
            fetchSpinner.style.display = loading ? 'inline-block' : 'none';
        }

        function showProgress() {
            document.getElementById('progressContainer').style.display = 'block';
        }

        function hideProgress() {
            document.getElementById('progressContainer').style.display = 'none';
        }

        function showStatus(message, type) {
            const statusEl = document.getElementById('statusMessage');
            statusEl.textContent = message;
            statusEl.className = 'status ' + type;
            statusEl.style.display = 'block';
        }

        function clearResults() {
            document.getElementById('resultsBox').innerHTML = '';
            document.getElementById('resultsContainer').style.display = 'block';
        }

        function addResultMessage(message, type) {
            const resultsBox = document.getElementById('resultsBox');
            const timestamp = new Date().toLocaleTimeString();
            
            const messageEl = document.createElement('div');
            messageEl.style.color = getColorForType(type);
            messageEl.style.marginBottom = '5px';
            messageEl.textContent = `[${timestamp}] ${message}`;
            
            resultsBox.appendChild(messageEl);
            resultsBox.scrollTop = resultsBox.scrollHeight;
        }

        function getColorForType(type) {
            switch(type) {
                case 'success': return '#059669';
                case 'error': return '#dc2626';
                case 'warning': return '#d97706';
                default: return '#2563eb';
            }
        }

        // Show initial status
        showStatus('Ready to fetch papers...', 'info');
    </script>
</body>
</html>
        """

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html_content.encode())

    def serve_status(self):
        """Serve status information"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        response = {'status': 'ready', 'message': 'Paper fetcher is ready'}
        self.wfile.write(json.dumps(response).encode())

    def handle_fetch_request(self):
        """Handle paper fetch requests"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))

        # Set up streaming response
        self.send_response(200)
        self.send_header('Content-type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.end_headers()

        # Start fetching papers in background
        fetcher = CrossrefPaperFetcher(self)
        fetcher.fetch_papers_async(data)

    def handle_open_folder(self):
        """Handle folder opening requests"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))

        try:
            file_path = data.get('file', '')
            if file_path and os.path.exists(file_path):
                directory = os.path.dirname(file_path)

                if sys.platform == "win32":
                    os.startfile(directory)
                elif sys.platform == "darwin":  # macOS
                    subprocess.run(["open", directory])
                else:  # Linux
                    subprocess.run(["xdg-open", directory])

                response = {'success': True, 'message': f'Opened {directory}'}
            else:
                response = {'success': False, 'error': 'File not found'}

        except Exception as e:
            response = {'success': False, 'error': str(e)}

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())

    def send_event(self, event_type, data):
        """Send server-sent event"""
        try:
            event_data = {
                'type': event_type,
                **data
            }
            event_str = f"data: {json.dumps(event_data)}\n\n"
            self.wfile.write(event_str.encode())
            self.wfile.flush()
        except:
            pass


class CrossrefPaperFetcher:
    """Paper fetcher with web interface support"""

    def __init__(self, handler):
        self.handler = handler
        self.base_url = "https://api.crossref.org/works"
        self.headers = {
            'User-Agent': 'ResearchHelper/1.0 (mailto:researcher@example.com)'
        }

    def fetch_papers_async(self, params):
        """Fetch papers asynchronously with progress updates"""
        try:
            keyword = params['keyword'].strip()
            additional_keyword = params.get('additional_keyword', '').strip()
            from_year = int(params['from_year'])
            to_year = int(params['to_year'])
            total_results = int(params['total_results'])
            title_filter = params.get('title_filter', True)
            paper_type_filter = params.get('paper_type_filter', True)

            self.handler.send_event('log', {
                'message': f"🔍  Papers fetching... Please wait",
                'level': 'info'
            })
            self.handler.send_event('log', {
                'message': f"Primary keyword: '{keyword}'",
                'level': 'info'
            })
            self.handler.send_event('log', {
                'message': f"Additional keyword: '{additional_keyword}'",
                'level': 'info'
            })
            self.handler.send_event('log', {
                'message': f"Year range: {from_year} to {to_year}",
                'level': 'info'
            })
            self.handler.send_event('log', {
                'message': f"Target results: {total_results}",
                'level': 'info'
            })
            self.handler.send_event('log', {
                'message': "-" * 60,
                'level': 'info'
            })

            papers = self.search_papers(keyword, additional_keyword, from_year,
                                      to_year, total_results, title_filter, paper_type_filter)

            if papers:
                output_file = self.save_to_csv(papers, keyword)
                self.display_summary(papers)

                self.handler.send_event('complete', {
                    'count': len(papers),
                    'file': output_file,
                    'message': f'Successfully fetched {len(papers)} papers!'
                })
            else:
                self.handler.send_event('error', {
                    'message': 'No papers found matching your criteria'
                })

        except Exception as e:
            self.handler.send_event('error', {
                'message': str(e)
            })

    def search_papers(self, keyword, additional_keyword, from_year, to_year, total_results, title_filter, paper_type_filter):
        """Search for papers using Crossref API with year range support"""
        papers = []
        rows_per_request = 20
        offset = 0
        fetched_count = 0
        processed_count = 0
        max_attempts = total_results * 5

        keyword_lower = keyword.lower().strip()
        additional_keyword_lower = additional_keyword.lower().strip() if additional_keyword.strip() else ""

        while fetched_count < total_results and processed_count < max_attempts:
            try:
                remaining = total_results - fetched_count
                current_rows = min(rows_per_request, remaining * 2)

                # Build query URL with year range support
                if additional_keyword.strip():
                    encoded_keyword = quote(keyword)
                    encoded_additional = quote(additional_keyword)
                    url = (f"{self.base_url}?query.title={encoded_keyword}+{encoded_additional}"
                          f"&filter=from-pub-date:{from_year},until-pub-date:{to_year},type:journal-article,type:proceedings-article"
                          f"&rows={current_rows}&offset={offset}&sort=relevance")
                else:
                    encoded_keyword = quote(keyword)
                    url = (f"{self.base_url}?query.title={encoded_keyword}"
                          f"&filter=from-pub-date:{from_year},until-pub-date:{to_year},type:journal-article,type:proceedings-article"
                          f"&rows={current_rows}&offset={offset}&sort=relevance")

                self.handler.send_event('log', {
                    'message': f"📡 Fetching papers {offset + 1} to {offset + current_rows}...",
                    'level': 'info'
                })

                # Make API request
                response = requests.get(url, headers=self.headers, timeout=15)
                response.raise_for_status()

                data = response.json()
                items = data.get('message', {}).get('items', [])

                if not items:
                    self.handler.send_event('log', {
                        'message': "⚠️ No more papers found",
                        'level': 'warning'
                    })
                    break

                # Process each paper
                for item in items:
                    processed_count += 1

                    if fetched_count >= total_results:
                        break

                    # Filter for paper types
                    if paper_type_filter:
                        paper_type = item.get('type', '')
                        if paper_type not in ['journal-article', 'proceedings-article']:
                            continue

                    # Extract title for filtering
                    title = ""
                    if 'title' in item and item['title']:
                        title = item['title'][0] if isinstance(item['title'], list) else item['title']

                    # Title filtering if enabled
                    if title_filter:
                        title_lower = title.lower()
                        keyword_in_title = keyword_lower in title_lower
                        additional_in_title = True

                        if additional_keyword_lower:
                            additional_in_title = additional_keyword_lower in title_lower

                        if not (keyword_in_title and additional_in_title):
                            continue

                    paper = self.extract_paper_info(item, fetched_count + 1)
                    papers.append(paper)
                    fetched_count += 1

                    if (fetched_count) % 5 == 0 or fetched_count == total_results:
                        self.handler.send_event('log', {
                            'message': f"   ✅ Found {fetched_count}/{total_results} qualifying papers",
                            'level': 'success'
                        })

                offset += current_rows
                time.sleep(0.2)  # Rate limiting

            except requests.exceptions.RequestException as e:
                self.handler.send_event('log', {
                    'message': f"❌ Error fetching data: {e}",
                    'level': 'error'
                })
                break
            except Exception as e:
                self.handler.send_event('log', {
                    'message': f"❌ Unexpected error: {e}",
                    'level': 'error'
                })
                break

        return papers

    def extract_paper_info(self, item: Dict, paper_id: int) -> Dict:
        """Extract paper information from Crossref API response"""
        # Extract authors
        authors = []
        if 'author' in item:
            for author in item['author']:
                if 'given' in author and 'family' in author:
                    authors.append(f"{author['given']} {author['family']}")
                elif 'family' in author:
                    authors.append(author['family'])

        # Extract title
        title = ""
        if 'title' in item and item['title']:
            title = item['title'][0] if isinstance(item['title'], list) else item['title']

        # Extract abstract
        abstract = ""
        if 'abstract' in item and item['abstract']:
            abstract = item['abstract']
            import re
            abstract = re.sub(r'<[^>]+>', '', abstract)
            abstract = re.sub(r'\s+', ' ', abstract).strip()

        # Extract journal
        journal = ""
        if 'container-title' in item and item['container-title']:
            journal = item['container-title'][0] if isinstance(item['container-title'], list) else item['container-title']

        # Extract year
        year = ""
        if 'published-print' in item and item['published-print'].get('date-parts'):
            year = str(item['published-print']['date-parts'][0][0])
        elif 'published-online' in item and item['published-online'].get('date-parts'):
            year = str(item['published-online']['date-parts'][0][0])

        return {
            'paper_id': f"paper_{paper_id:03d}",
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

    def save_to_csv(self, papers: List[Dict], keyword: str) -> str:
        """Save papers to CSV file"""
        # Set output directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(os.path.dirname(current_dir))
        output_dir = os.path.join(project_dir, 'results', 'custom', '1')

        # Create directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Create DataFrame and save
        df = pd.DataFrame(papers)

        # Generate filename
        safe_keyword = "".join(c for c in keyword if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_keyword = safe_keyword.replace(' ', '_').lower()
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"crossref_papers_{safe_keyword}_{timestamp}.csv"
        filepath = os.path.join(output_dir, filename)

        df.to_csv(filepath, index=False)
        return filepath

    def display_summary(self, papers: List[Dict]):
        """Display summary of fetched papers"""
        self.handler.send_event('log', {
            'message': "\n📊 FETCH SUMMARY",
            'level': 'info'
        })
        self.handler.send_event('log', {
            'message': "=" * 50,
            'level': 'info'
        })
        self.handler.send_event('log', {
            'message': f"Total papers: {len(papers)}",
            'level': 'success'
        })

        # Count by year
        years = [p['year'] for p in papers if p['year']]
        if years:
            year_counts = {}
            for year in years:
                year_counts[year] = year_counts.get(year, 0) + 1

            self.handler.send_event('log', {
                'message': "\nPapers by year:",
                'level': 'info'
            })
            for year in sorted(year_counts.keys(), reverse=True)[:5]:
                self.handler.send_event('log', {
                    'message': f"  {year}: {year_counts[year]} papers",
                    'level': 'info'
                })

        # Show sample papers
        self.handler.send_event('log', {
            'message': "\n📄 SAMPLE PAPERS:",
            'level': 'info'
        })
        self.handler.send_event('log', {
            'message': "-" * 50,
            'level': 'info'
        })
        for i, paper in enumerate(papers[:3]):
            self.handler.send_event('log', {
                'message': f"{i+1}. {paper['title'][:60]}...",
                'level': 'success'
            })
            self.handler.send_event('log', {
                'message': f"   Authors: {paper['authors'][:50]}...",
                'level': 'info'
            })
            self.handler.send_event('log', {
                'message': f"   Journal: {paper['journal']}",
                'level': 'info'
            })
            self.handler.send_event('log', {
                'message': f"   Year: {paper['year']}\n",
                'level': 'info'
            })


def main():
    """Main function to run the web GUI"""
    port = 8000

    # Find an available port
    while True:
        try:
            server = HTTPServer(('localhost', port), PaperFetcherHandler)
            break
        except OSError:
            port += 1
            if port > 8010:
                print("Could not find an available port")
                return

    print(f"🚀 Starting Research Paper Fetcher Web GUI...")
    print(f"🌐 Server running at: http://localhost:{port}")
    print(f"📁 Results will be saved to: scripts/results/custom/1/")
    print("🔗 Opening browser automatically...")

    # Open browser automatically
    webbrowser.open(f'http://localhost:{port}')

    # Start server
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n⏹️ Server stopped by user")
        server.shutdown()


if __name__ == "__main__":
    main()
