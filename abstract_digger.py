#!/usr/bin/env python3
"""
Enhanced Abstract Digger - Research Paper Abstract and PDF Fetcher
Fetches abstracts and PDFs from multiple sources including Semantic Scholar, arXiv, CrossRef, and web scraping
"""

import pandas as pd
import requests
import time
import os
import re
import json
from datetime import datetime
from urllib.parse import urlparse, quote
import argparse
from typing import Dict, List, Optional, Tuple
import logging
from bs4 import BeautifulSoup
import hashlib

class AbstractDigger:
    def __init__(self, output_dir: str = "/Users/reddy/2025/ResearchHelper/results"):
        self.output_dir = output_dir
        self.pdf_dir = os.path.join(output_dir, "pdf")
        os.makedirs(self.pdf_dir, exist_ok=True)

        # Setup logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

        # Rate limiting
        self.last_request_time = 0
        self.min_delay = 1.0  # seconds between requests

        # Session for persistent connections
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ResearchHelper/1.0 (mailto:researcher@example.com)'
        })

    def rate_limit(self):
        """Implement rate limiting between API calls"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_delay:
            time.sleep(self.min_delay - time_since_last)
        self.last_request_time = time.time()

    def search_semantic_scholar(self, title: str) -> Dict:
        """Search Semantic Scholar API for paper information"""
        self.rate_limit()

        try:
            # Clean title for search
            clean_title = re.sub(r'[^\w\s]', ' ', title).strip()

            # Search by title
            search_url = f"https://api.semanticscholar.org/graph/v1/paper/search"
            params = {
                'query': clean_title,
                'fields': 'paperId,title,abstract,authors,journal,year,venue,citationCount,openAccessPdf,url,externalIds'
            }

            response = self.session.get(search_url, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                if data.get('data') and len(data['data']) > 0:
                    # Find best match
                    for paper in data['data']:
                        if self.title_similarity(title, paper.get('title', '')) > 0.8:
                            return {
                                'found': True,
                                'abstract': paper.get('abstract', ''),
                                'paper_data': paper,
                                'source': 'Semantic Scholar',
                                'confidence': 'high'
                            }

                    # If no high similarity, take first result with lower confidence
                    return {
                        'found': True,
                        'abstract': data['data'][0].get('abstract', ''),
                        'paper_data': data['data'][0],
                        'source': 'Semantic Scholar',
                        'confidence': 'medium'
                    }

        except Exception as e:
            self.logger.error(f"Semantic Scholar search error for '{title}': {e}")

        return {'found': False, 'abstract': '', 'source': 'Semantic Scholar', 'confidence': 'none'}

    def search_arxiv(self, title: str) -> Dict:
        """Search arXiv API for paper information"""
        self.rate_limit()

        try:
            # Clean title for arXiv search
            clean_title = re.sub(r'[^\w\s]', ' ', title).strip()
            search_query = quote(clean_title)

            url = f"http://export.arxiv.org/api/query?search_query=ti:{search_query}&max_results=5"

            response = self.session.get(url, timeout=30)
            if response.status_code == 200:
                # Parse XML response
                from xml.etree import ElementTree as ET
                root = ET.fromstring(response.content)

                for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
                    entry_title = entry.find('{http://www.w3.org/2005/Atom}title').text.strip()
                    if self.title_similarity(title, entry_title) > 0.8:
                        summary = entry.find('{http://www.w3.org/2005/Atom}summary').text.strip()
                        pdf_link = None

                        # Get PDF link
                        for link in entry.findall('{http://www.w3.org/2005/Atom}link'):
                            if link.get('type') == 'application/pdf':
                                pdf_link = link.get('href')
                                break

                        return {
                            'found': True,
                            'abstract': summary,
                            'pdf_url': pdf_link,
                            'source': 'arXiv',
                            'confidence': 'high'
                        }

        except Exception as e:
            self.logger.error(f"arXiv search error for '{title}': {e}")

        return {'found': False, 'abstract': '', 'source': 'arXiv', 'confidence': 'none'}

    def search_crossref(self, title: str, doi: str = None) -> Dict:
        """Search CrossRef API for paper information"""
        self.rate_limit()

        try:
            if doi:
                # Search by DOI
                url = f"https://api.crossref.org/works/{doi}"
            else:
                # Search by title
                clean_title = re.sub(r'[^\w\s]', ' ', title).strip()
                url = f"https://api.crossref.org/works?query.title={quote(clean_title)}&rows=5"

            response = self.session.get(url, timeout=30)
            if response.status_code == 200:
                data = response.json()

                if doi:
                    # Direct DOI lookup
                    work = data.get('message', {})
                    abstract = work.get('abstract', '')
                    if abstract:
                        return {
                            'found': True,
                            'abstract': abstract,
                            'source': 'CrossRef',
                            'confidence': 'high'
                        }
                else:
                    # Title search
                    items = data.get('message', {}).get('items', [])
                    for item in items:
                        item_title = ' '.join(item.get('title', []))
                        if self.title_similarity(title, item_title) > 0.8:
                            abstract = item.get('abstract', '')
                            if abstract:
                                return {
                                    'found': True,
                                    'abstract': abstract,
                                    'source': 'CrossRef',
                                    'confidence': 'high'
                                }

        except Exception as e:
            self.logger.error(f"CrossRef search error for '{title}': {e}")

        return {'found': False, 'abstract': '', 'source': 'CrossRef', 'confidence': 'none'}

    def web_scrape_abstract(self, title: str, url: str = None) -> Dict:
        """Attempt to scrape abstract from web sources"""
        if not url:
            return {'found': False, 'abstract': '', 'source': 'Web Scraping', 'confidence': 'none'}

        self.rate_limit()

        try:
            response = self.session.get(url, timeout=30)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')

                # Common abstract selectors
                abstract_selectors = [
                    '.abstract',
                    '#abstract',
                    '[data-testid="abstract"]',
                    '.paper-abstract',
                    '.article-abstract',
                    'section[class*="abstract"]',
                    'div[class*="abstract"]'
                ]

                for selector in abstract_selectors:
                    abstract_elem = soup.select_one(selector)
                    if abstract_elem:
                        abstract_text = abstract_elem.get_text().strip()
                        if len(abstract_text) > 100:  # Reasonable abstract length
                            return {
                                'found': True,
                                'abstract': abstract_text,
                                'source': 'Web Scraping',
                                'confidence': 'medium'
                            }

        except Exception as e:
            self.logger.error(f"Web scraping error for '{title}': {e}")

        return {'found': False, 'abstract': '', 'source': 'Web Scraping', 'confidence': 'none'}

    def download_pdf(self, paper_id: str, pdf_url: str) -> Tuple[bool, str]:
        """Download PDF from given URL"""
        if not pdf_url:
            return False, "No PDF URL provided"

        try:
            self.rate_limit()

            response = self.session.get(pdf_url, timeout=60, stream=True)
            if response.status_code == 200:
                # Create filename
                filename = f"{paper_id}.pdf"
                filepath = os.path.join(self.pdf_dir, filename)

                # Download and save
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                # Verify file size
                if os.path.getsize(filepath) > 1000:  # At least 1KB
                    return True, filepath
                else:
                    os.remove(filepath)
                    return False, "Downloaded file too small"

        except Exception as e:
            self.logger.error(f"PDF download error for {paper_id}: {e}")
            return False, str(e)

        return False, f"HTTP {response.status_code}"

    def title_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between two titles"""
        if not title1 or not title2:
            return 0.0

        # Simple word-based similarity
        words1 = set(re.findall(r'\w+', title1.lower()))
        words2 = set(re.findall(r'\w+', title2.lower()))

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union)

    def categorize_paper(self, title: str, abstract: str) -> Dict:
        """Categorize paper based on title and abstract"""
        text = f"{title} {abstract}".lower()

        # Define categories and keywords
        categories = {
            'Survey': ['survey', 'review', 'systematic', 'taxonomy', 'classification'],
            'Latency': ['latency', 'cold start', 'startup', 'boot', 'initialization', 'response time'],
            'Reliability': ['reliability', 'fault', 'failure', 'availability', 'resilience', 'qos'],
            'Security': ['security', 'privacy', 'authentication', 'authorization', 'encryption'],
            'Cost': ['cost', 'pricing', 'billing', 'economic', 'budget', 'expense'],
            'Energy Consumption': ['energy', 'power', 'consumption', 'efficiency', 'green'],
            'Resource Management': ['resource', 'scaling', 'allocation', 'management', 'optimization'],
            'Benchmark': ['benchmark', 'evaluation', 'comparison', 'performance', 'measurement']
        }

        detected_categories = []
        detected_keywords = []

        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in text:
                    if category not in detected_categories:
                        detected_categories.append(category)
                    detected_keywords.append(keyword)

        return {
            'original_category': ', '.join(detected_categories) if detected_categories else 'Others',
            'original_keywords': ', '.join(set(detected_keywords))
        }

    def extract_contributions_limitations(self, abstract: str) -> Dict:
        """Extract contributions and limitations from abstract"""
        if not abstract:
            return {'contributions': 'Not available', 'limitations': 'Not explicitly mentioned'}

        # Simple heuristic-based extraction
        contributions = []
        limitations = []

        sentences = re.split(r'[.!?]', abstract)

        for sentence in sentences:
            sentence = sentence.strip().lower()

            # Contribution indicators
            contrib_indicators = ['we propose', 'we introduce', 'we present', 'we show', 'we demonstrate',
                                'this paper', 'our approach', 'our method', 'our system', 'contribution']

            if any(indicator in sentence for indicator in contrib_indicators):
                contributions.append(sentence.strip())

            # Limitation indicators
            limit_indicators = ['limitation', 'drawback', 'weakness', 'however', 'but', 'challenge',
                              'difficult', 'problem', 'issue']

            if any(indicator in sentence for indicator in limit_indicators):
                limitations.append(sentence.strip())

        return {
            'contributions': '; '.join(contributions[:3]) if contributions else 'Not explicitly mentioned',
            'limitations': '; '.join(limitations[:2]) if limitations else 'Not explicitly mentioned'
        }

    def process_papers(self, csv_path: str) -> pd.DataFrame:
        """Process papers from CSV file"""
        # Read input CSV
        df = pd.read_csv(csv_path)
        self.logger.info(f"Processing {len(df)} papers from {csv_path}")

        # Initialize new columns
        df['abstract'] = df.get('abstract', '')
        df['abstract_source'] = ''
        df['abstract_confidence'] = ''
        df['original_category'] = ''
        df['original_keywords'] = ''
        df['contributions'] = ''
        df['limitations'] = ''
        df['pdf_downloaded'] = False
        df['pdf_path'] = ''

        # Ensure paper_id exists
        if 'paper_id' not in df.columns:
            df['paper_id'] = df.index.map(lambda x: f"paper_{x+1:03d}")

        success_count = 0
        pdf_count = 0

        for idx, row in df.iterrows():
            title = row.get('title', '')
            existing_abstract = row.get('abstract', '')
            paper_id = row.get('paper_id', f"paper_{idx+1:03d}")
            doi = row.get('doi', '')
            url = row.get('url', '')

            self.logger.info(f"Processing paper {idx+1}/{len(df)}: {title[:50]}...")

            # Handle existing abstract - ensure it's a string
            existing_abstract_str = str(existing_abstract) if existing_abstract is not None else ''
            if existing_abstract_str and len(existing_abstract_str.strip()) > 50:
                # Use existing abstract
                abstract_info = {
                    'found': True,
                    'abstract': existing_abstract,
                    'source': 'Existing',
                    'confidence': 'high'
                }
            else:
                # Try to fetch abstract from multiple sources
                abstract_info = None

                # Try Semantic Scholar first
                if not abstract_info or not abstract_info['found']:
                    abstract_info = self.search_semantic_scholar(title)

                # Try arXiv
                if not abstract_info['found']:
                    arxiv_result = self.search_arxiv(title)
                    if arxiv_result['found']:
                        abstract_info = arxiv_result
                        # Try to download PDF from arXiv
                        if arxiv_result.get('pdf_url'):
                            pdf_success, pdf_path = self.download_pdf(paper_id, arxiv_result['pdf_url'])
                            if pdf_success:
                                df.at[idx, 'pdf_downloaded'] = True
                                df.at[idx, 'pdf_path'] = pdf_path
                                pdf_count += 1

                # Try CrossRef
                if not abstract_info['found']:
                    abstract_info = self.search_crossref(title, doi)

                # Try web scraping as last resort
                if not abstract_info['found'] and url:
                    abstract_info = self.web_scrape_abstract(title, url)

            # Update dataframe with abstract information
            if abstract_info and abstract_info['found']:
                df.at[idx, 'abstract'] = abstract_info['abstract']
                df.at[idx, 'abstract_source'] = abstract_info['source']
                df.at[idx, 'abstract_confidence'] = abstract_info['confidence']
                success_count += 1

                # Categorize paper
                categorization = self.categorize_paper(title, abstract_info['abstract'])
                df.at[idx, 'original_category'] = categorization['original_category']
                df.at[idx, 'original_keywords'] = categorization['original_keywords']

                # Extract contributions and limitations
                contrib_limit = self.extract_contributions_limitations(abstract_info['abstract'])
                df.at[idx, 'contributions'] = contrib_limit['contributions']
                df.at[idx, 'limitations'] = contrib_limit['limitations']

                # Try to download PDF from Semantic Scholar if available
                if abstract_info.get('paper_data') and not df.at[idx, 'pdf_downloaded']:
                    paper_data = abstract_info['paper_data']
                    if paper_data.get('openAccessPdf') and paper_data['openAccessPdf'].get('url'):
                        pdf_success, pdf_path = self.download_pdf(paper_id, paper_data['openAccessPdf']['url'])
                        if pdf_success:
                            df.at[idx, 'pdf_downloaded'] = True
                            df.at[idx, 'pdf_path'] = pdf_path
                            pdf_count += 1

            # Progress update every 10 papers
            if (idx + 1) % 10 == 0:
                self.logger.info(f"Processed {idx + 1}/{len(df)} papers. Success rate: {success_count/(idx+1)*100:.1f}%")

        # Sort by abstract availability (papers with abstracts first)
        df_with_abstract = df[df['abstract'].str.len() > 50].copy()
        df_without_abstract = df[df['abstract'].str.len() <= 50].copy()

        # Reassign paper IDs
        for idx, row in enumerate(df_with_abstract.index):
            df_with_abstract.at[row, 'paper_id'] = f"paper_{idx+1:03d}"

        start_idx = len(df_with_abstract)
        for idx, row in enumerate(df_without_abstract.index):
            df_without_abstract.at[row, 'paper_id'] = f"paper_{start_idx + idx + 1:03d}"

        # Combine dataframes
        final_df = pd.concat([df_with_abstract, df_without_abstract], ignore_index=True)

        # Print summary
        self.logger.info(f"\nSUMMARY:")
        self.logger.info(f"Total papers processed: {len(final_df)}")
        self.logger.info(f"Papers with abstracts: {success_count}")
        self.logger.info(f"PDFs downloaded: {pdf_count}")
        self.logger.info(f"Success rate: {success_count/len(final_df)*100:.1f}%")
        self.logger.info(f"PDF download rate: {pdf_count/len(final_df)*100:.1f}%")

        return final_df

def main():
    # Interactive mode - ask for input path
    input_path = input("Enter the path to your CSV file: ").strip()

    # Validate input file exists
    if not os.path.exists(input_path):
        print(f"Error: File '{input_path}' not found!")
        return

    # Ask for output directory
    output_dir = input("Enter output directory (press Enter for default: results/final/): ").strip()
    if not output_dir:
        output_dir = "/Users/reddy/2025/ResearchHelper/results/final"

    os.makedirs(output_dir, exist_ok=True)

    # Initialize digger
    digger = AbstractDigger(output_dir)

    # Process papers
    result_df = digger.process_papers(input_path)

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"enhanced_papers_with_abstracts_{timestamp}.csv"
    output_path = os.path.join(output_dir, output_filename)

    result_df.to_csv(output_path, index=False)
    print(f"\nResults saved to: {output_path}")

if __name__ == "__main__":
    main()
