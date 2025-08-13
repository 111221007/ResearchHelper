#!/usr/bin/env python3
"""
Multi-Keyword Research Paper Pipeline
Fetches papers for multiple keywords, combines them, and processes through the full pipeline
"""

import pandas as pd
import requests
import time
import os
import re
import json
from datetime import datetime
from urllib.parse import urlparse, quote
from typing import Dict, List, Optional, Tuple, Set
import logging
import hashlib
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed

class MultiKeywordPaperFetcher:
    def __init__(self, output_dir: str = "/Users/reddy/2025/ResearchHelper/results"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        # Setup logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

        # Rate limiting
        self.last_request_time = 0
        self.min_delay = 0.5  # seconds between requests

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

    def fetch_papers_for_keyword(self, primary_keyword: str, secondary_keyword: str = "",
                                from_year: int = 2020, to_year: int = 2025,
                                max_results: int = 50) -> List[Dict]:
        """Fetch papers for a specific keyword combination"""
        papers = []

        try:
            self.logger.info(f"Fetching papers for: '{primary_keyword}' + '{secondary_keyword}'")

            # Build query
            if secondary_keyword.strip():
                query = f"{primary_keyword} {secondary_keyword}"
                search_term = f"{primary_keyword}+{secondary_keyword}"
            else:
                query = primary_keyword
                search_term = primary_keyword

            # Fetch from CrossRef
            crossref_papers = self._fetch_from_crossref(search_term, from_year, to_year, max_results)
            papers.extend(crossref_papers)

            # Fetch from arXiv
            arxiv_papers = self._fetch_from_arxiv(query, max_results // 4)
            papers.extend(arxiv_papers)

            # Add keyword source info
            for paper in papers:
                paper['search_keywords'] = f"{primary_keyword}; {secondary_keyword}".strip('; ')
                paper['fetch_source'] = 'CrossRef+arXiv'

            self.logger.info(f"Fetched {len(papers)} papers for '{query}'")
            return papers

        except Exception as e:
            self.logger.error(f"Error fetching papers for '{primary_keyword}': {e}")
            return []

    def _fetch_from_crossref(self, search_term: str, from_year: int, to_year: int, max_results: int) -> List[Dict]:
        """Fetch papers from CrossRef API"""
        papers = []
        rows_per_request = 50
        offset = 0

        while len(papers) < max_results:
            try:
                self.rate_limit()

                remaining = max_results - len(papers)
                current_rows = min(rows_per_request, remaining * 2)  # Fetch more to account for filtering

                url = f"https://api.crossref.org/works?"
                url += f"query.title={quote(search_term)}"
                url += f"&filter=from-pub-date:{from_year},until-pub-date:{to_year}"
                url += ",type:journal-article,type:proceedings-article"
                url += f"&rows={current_rows}&offset={offset}&sort=relevance"

                response = self.session.get(url, timeout=30)
                if response.status_code != 200:
                    break

                data = response.json()
                items = data.get('message', {}).get('items', [])

                if not items:
                    break

                for idx, item in enumerate(items):
                    if len(papers) >= max_results:
                        break

                    paper = self._extract_crossref_paper(item, len(papers) + 1)
                    if paper:
                        papers.append(paper)

                offset += current_rows

                # Break if we got fewer results than requested (end of results)
                if len(items) < current_rows:
                    break

            except Exception as e:
                self.logger.error(f"CrossRef fetch error: {e}")
                break

        return papers[:max_results]

    def _fetch_from_arxiv(self, query: str, max_results: int) -> List[Dict]:
        """Fetch papers from arXiv API"""
        papers = []

        try:
            self.rate_limit()

            search_query = quote(query)
            url = f"http://export.arxiv.org/api/query?search_query=all:{search_query}&max_results={max_results}"

            response = self.session.get(url, timeout=30)
            if response.status_code == 200:
                from xml.etree import ElementTree as ET
                root = ET.fromstring(response.content)

                for idx, entry in enumerate(root.findall('{http://www.w3.org/2005/Atom}entry')):
                    paper = self._extract_arxiv_paper(entry, len(papers) + 1)
                    if paper:
                        papers.append(paper)

        except Exception as e:
            self.logger.error(f"arXiv fetch error: {e}")

        return papers

    def _extract_crossref_paper(self, item: Dict, paper_id: int) -> Optional[Dict]:
        """Extract paper information from CrossRef item"""
        try:
            # Extract authors
            authors = []
            if item.get('author'):
                for author in item['author']:
                    if author.get('given') and author.get('family'):
                        authors.append(f"{author['given']} {author['family']}")
                    elif author.get('family'):
                        authors.append(author['family'])

            # Extract title - handle both string and float
                title_val = item['title'][0] if isinstance(item['title'], list) else item['title']
                title = str(title_val).strip() if title_val is not None else ''
            # Extract journal - handle both string and float
                journal_val = item['container-title'][0] if isinstance(item['container-title'], list) else item['container-title']
                journal = str(journal_val).strip() if journal_val is not None else ''
            # Handle abstract - ensure it's a string
            abstract_val = item.get('abstract', '')
            abstract = str(abstract_val).strip() if abstract_val is not None else ''

                'title': title,
                'abstract': abstract,
                'journal': journal,
                'volume': str(item.get('volume', '')) if item.get('volume') is not None else '',
                'issue': str(item.get('issue', '')) if item.get('issue') is not None else '',
                'pages': str(item.get('page', '')) if item.get('page') is not None else '',
                'publisher': str(item.get('publisher', '')) if item.get('publisher') is not None else '',
                'doi': str(item.get('DOI', '')) if item.get('DOI') is not None else '',
                'url': str(item.get('URL', '')) if item.get('URL') is not None else '',
                'type': str(item.get('type', '')) if item.get('type') is not None else '',
            
                year = str(item['published-online']['date-parts'][0][0])

            # Skip if essential fields are missing
            if not title or not year:
                return None

            return {
                'paper_id': f"paper_{paper_id:03d}",
                'title': title.strip(),
                'abstract': item.get('abstract', '').strip(),
                'authors': '; '.join(authors) if authors else 'Not Available',
                'journal': journal.strip(),
                'year': year,
                'volume': item.get('volume', ''),
                'issue': item.get('issue', ''),
                'pages': item.get('page', ''),
                'publisher': item.get('publisher', ''),
                'doi': item.get('DOI', ''),
                'url': item.get('URL', ''),
                'type': item.get('type', ''),
                'abstract_source': '',
                'abstract_confidence': '',
                'original_category': '',
                'original_keywords': '',
                'contributions': '',
                'limitations': ''
            }

        except Exception as e:
            self.logger.error(f"Error extracting CrossRef paper: {e}")
            return None

    def _extract_arxiv_paper(self, entry, paper_id: int) -> Optional[Dict]:
        """Extract paper information from arXiv entry"""
        try:
            title = entry.find('{http://www.w3.org/2005/Atom}title').text.strip()
            abstract = entry.find('{http://www.w3.org/2005/Atom}summary').text.strip()

            # Extract authors
            authors = []
            for author in entry.findall('{http://www.w3.org/2005/Atom}author'):
                name = author.find('{http://www.w3.org/2005/Atom}name').text
                authors.append(name)

            # Extract year from published date
            published = entry.find('{http://www.w3.org/2005/Atom}published').text
            year = published.split('-')[0]

            # Extract PDF URL
            pdf_url = ''
            for link in entry.findall('{http://www.w3.org/2005/Atom}link'):
                if link.get('type') == 'application/pdf':
                    pdf_url = link.get('href')
                    break

            return {
                'paper_id': f"paper_{paper_id:03d}",
                'title': title,
                'abstract': abstract,
                'authors': '; '.join(authors) if authors else 'Not Available',
                'journal': 'arXiv preprint',
                'year': year,
                'volume': '',
                'issue': '',
                'pages': '',
                'publisher': 'arXiv',
                'doi': '',
                'url': pdf_url,
                'type': 'preprint',
                'abstract_source': 'arXiv',
                'abstract_confidence': 'high' if abstract else 'none',
                'original_category': '',
                'original_keywords': '',
                'contributions': '',
                'limitations': ''
            }

        except Exception as e:
            self.logger.error(f"Error extracting arXiv paper: {e}")
            return None

    def calculate_similarity(self, title1: str, title2: str, threshold: float = 0.8) -> float:
        """Calculate similarity between two titles"""
        if not title1 or not title2:
            return 0.0

        # Normalize titles
        title1_clean = re.sub(r'[^\w\s]', ' ', title1.lower()).strip()
        title2_clean = re.sub(r'[^\w\s]', ' ', title2.lower()).strip()

        words1 = set(title1_clean.split())
        words2 = set(title2_clean.split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0.0

    def remove_duplicates(self, papers: List[Dict]) -> List[Dict]:
        """Remove duplicate papers based on title similarity and DOI"""
        unique_papers = []
        seen_dois = set()
        processed_titles = []

        self.logger.info(f"Removing duplicates from {len(papers)} papers...")

        for paper in papers:
            is_duplicate = False

            # Check DOI first (exact match)
            doi = paper.get('doi', '').strip()
            if doi and doi in seen_dois:
                is_duplicate = True
            elif doi:
                seen_dois.add(doi)

            # Check title similarity
            if not is_duplicate:
                title = paper.get('title', '').strip()
                for existing_title in processed_titles:
                    if self.calculate_similarity(title, existing_title) > 0.85:
                        is_duplicate = True
                        break

                if not is_duplicate:
                    processed_titles.append(title)

            if not is_duplicate:
                unique_papers.append(paper)

        removed_count = len(papers) - len(unique_papers)
        self.logger.info(f"Removed {removed_count} duplicates, {len(unique_papers)} unique papers remaining")

        return unique_papers

    def reassign_paper_ids(self, papers: List[Dict]) -> List[Dict]:
        """Reassign paper IDs sequentially"""
        for idx, paper in enumerate(papers, 1):
            paper['paper_id'] = f"paper_{idx:03d}"
        return papers

    def save_intermediate_csv(self, papers: List[Dict], filename: str) -> str:
        """Save papers to intermediate CSV file"""
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

        filepath = os.path.join(self.output_dir, filename)
        df.to_csv(filepath, index=False)
        self.logger.info(f"Saved {len(papers)} papers to {filepath}")

        return filepath

    def fetch_multi_keyword_papers(self, keyword_configs: List[Dict]) -> str:
        """
        Fetch papers for multiple keyword configurations

        Args:
            keyword_configs: List of dicts with keys: primary_keyword, secondary_keyword,
                           from_year, to_year, max_results

        Returns:
            Path to the combined CSV file
        """
        all_papers = []
        intermediate_files = []

        self.logger.info(f"Starting multi-keyword paper fetch for {len(keyword_configs)} configurations")

        # Fetch papers for each keyword configuration
        for idx, config in enumerate(keyword_configs, 1):
            primary = config.get('primary_keyword', '').strip()
            secondary = config.get('secondary_keyword', '').strip()
            from_year = config.get('from_year', 2020)
            to_year = config.get('to_year', 2025)
            max_results = config.get('max_results', 50)

            if not primary:
                self.logger.warning(f"Skipping config {idx}: No primary keyword provided")
                continue

            self.logger.info(f"Processing configuration {idx}/{len(keyword_configs)}")

            # Fetch papers for this configuration
            papers = self.fetch_papers_for_keyword(
                primary, secondary, from_year, to_year, max_results
            )

            if papers:
                # Save intermediate CSV
                filename = f"csv_{idx}_{primary.replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                filepath = self.save_intermediate_csv(papers, filename)
                intermediate_files.append(filepath)

                all_papers.extend(papers)
                self.logger.info(f"Added {len(papers)} papers from configuration {idx}")

            # Small delay between configurations
            time.sleep(1)

        if not all_papers:
            raise ValueError("No papers were fetched from any configuration")

        self.logger.info(f"Total papers fetched before deduplication: {len(all_papers)}")

        # Remove duplicates
        unique_papers = self.remove_duplicates(all_papers)

        # Reassign paper IDs
        unique_papers = self.reassign_paper_ids(unique_papers)

        # Save combined CSV
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        combined_filename = f"combined_papers_deduplicated_{timestamp}.csv"
        combined_filepath = self.save_intermediate_csv(unique_papers, combined_filename)

        # Log summary
        self.logger.info(f"FETCH SUMMARY:")
        self.logger.info(f"Configurations processed: {len(keyword_configs)}")
        self.logger.info(f"Intermediate CSV files: {len(intermediate_files)}")
        self.logger.info(f"Total papers before deduplication: {len(all_papers)}")
        self.logger.info(f"Unique papers after deduplication: {len(unique_papers)}")
        self.logger.info(f"Combined CSV saved to: {combined_filepath}")

        return combined_filepath


# Example usage and testing
if __name__ == "__main__":
    # Example configurations
    keyword_configs = [
        {
            'primary_keyword': 'serverless computing',
            'secondary_keyword': 'performance',
            'from_year': 2020,
            'to_year': 2025,
            'max_results': 30
        },
        {
            'primary_keyword': 'serverless',
            'secondary_keyword': 'security',
            'from_year': 2020,
            'to_year': 2025,
            'max_results': 30
        },
        {
            'primary_keyword': 'serverless',
            'secondary_keyword': 'cost optimization',
            'from_year': 2021,
            'to_year': 2025,
            'max_results': 25
        }
    ]

    fetcher = MultiKeywordPaperFetcher()
    try:
        combined_csv_path = fetcher.fetch_multi_keyword_papers(keyword_configs)
        print(f"\n✅ Multi-keyword fetch completed!")
        print(f"Combined CSV available at: {combined_csv_path}")
    except Exception as e:
        print(f"❌ Error: {e}")
