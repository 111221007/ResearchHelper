#!/usr/bin/env python3
"""
Enhanced citation generator that fetches complete citation information from online sources.
Uses Semantic Scholar API and Google Scholar to get real citation data.
"""

import pandas as pd
import time
import os
import requests
import json
from typing import List, Dict, Optional
from scholarly import scholarly
import re

class EnhancedCitationGenerator:
    """
    Generate complete citations by fetching data from online academic sources.
    """

    def __init__(self, delay: float = 1.0):
        self.delay = delay
        self.session = requests.Session()
        # Add headers to avoid being blocked
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

    def read_papers_from_csv(self, csv_file_path: str) -> List[Dict]:
        """Read all papers from consolidated CSV file."""
        papers = []
        try:
            df = pd.read_csv(csv_file_path)
            for _, row in df.iterrows():
                paper = {
                    'id': row.get('consolidated_id', ''),
                    'title': row.get('title', ''),
                    'year': str(row.get('year', '')),
                    'venue': row.get('venue', ''),
                    'category': row.get('category', ''),
                    'keywords': row.get('keywords', ''),
                }
                papers.append(paper)
            print(f"Successfully loaded {len(papers)} papers from CSV")
        except Exception as e:
            print(f"Error reading CSV file: {e}")

        return papers

    def search_semantic_scholar(self, title: str) -> Optional[Dict]:
        """Search Semantic Scholar API for paper details."""
        try:
            # Clean title for search
            clean_title = title.strip()

            # Use Semantic Scholar search API
            url = "https://api.semanticscholar.org/graph/v1/paper/search"
            params = {
                'query': clean_title,
                'limit': 1,
                'fields': 'title,authors,venue,year,journal,volume,pages,publicationTypes,externalIds'
            }

            response = self.session.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get('data') and len(data['data']) > 0:
                    paper = data['data'][0]

                    # Extract citation information
                    citation = self.extract_semantic_scholar_info(paper)
                    return citation

            return None

        except Exception as e:
            print(f"Error searching Semantic Scholar for '{title[:50]}...': {e}")
            return None

    def extract_semantic_scholar_info(self, paper: Dict) -> Dict:
        """Extract citation info from Semantic Scholar response."""
        citation = {
            'title': paper.get('title', ''),
            'authors': [],
            'journal': paper.get('venue', ''),
            'year': str(paper.get('year', '')),
            'volume': '',
            'number': '',
            'pages': '',
            'publisher': '',
            'doi': '',
            'source': 'semantic_scholar'
        }

        # Extract authors
        if paper.get('authors'):
            authors = []
            for author in paper['authors']:
                name = author.get('name', '')
                if name:
                    authors.append(name)
            citation['authors'] = authors

        # Extract DOI
        if paper.get('externalIds') and paper['externalIds'].get('DOI'):
            citation['doi'] = paper['externalIds']['DOI']

        # Try to extract volume, number, pages from venue or other fields
        journal_info = paper.get('journal', {})
        if journal_info:
            citation['volume'] = journal_info.get('volume', '')
            citation['pages'] = journal_info.get('pages', '')

        return citation

    def search_google_scholar(self, title: str) -> Optional[Dict]:
        """Search Google Scholar for paper details."""
        try:
            # Search for the publication
            search_query = scholarly.search_pubs(title)
            publication = next(search_query, None)

            if publication:
                # Fill in additional details
                pub_filled = scholarly.fill(publication)
                return self.extract_google_scholar_info(pub_filled)

            return None

        except Exception as e:
            print(f"Error searching Google Scholar for '{title[:50]}...': {e}")
            return None

    def extract_google_scholar_info(self, publication) -> Dict:
        """Extract citation info from Google Scholar response."""
        bib = publication.get('bib', {})

        citation = {
            'title': bib.get('title', ''),
            'authors': bib.get('author', []),
            'journal': bib.get('venue', ''),
            'year': str(bib.get('pub_year', '')),
            'volume': bib.get('volume', ''),
            'number': bib.get('number', ''),
            'pages': bib.get('pages', ''),
            'publisher': bib.get('publisher', ''),
            'doi': '',
            'source': 'google_scholar'
        }

        # Handle authors list
        if isinstance(citation['authors'], str):
            # Split author string if it's a single string
            citation['authors'] = [name.strip() for name in citation['authors'].split(' and ')]

        return citation

    def get_complete_citation(self, title: str) -> Optional[Dict]:
        """Get complete citation info by trying multiple sources."""
        print(f"Searching for: {title[:60]}...")

        # Try Semantic Scholar first (often more reliable for academic papers)
        citation = self.search_semantic_scholar(title)
        if citation and citation.get('authors'):
            print(f"✓ Found via Semantic Scholar: {title[:60]}...")
            return citation

        # Add delay between requests
        time.sleep(self.delay)

        # Try Google Scholar as fallback
        citation = self.search_google_scholar(title)
        if citation and citation.get('authors'):
            print(f"✓ Found via Google Scholar: {title[:60]}...")
            return citation

        print(f"✗ No complete citation found: {title[:60]}...")
        return None

    def format_bibtex_entry(self, citation: Dict, cite_key: str) -> str:
        """Format citation as BibTeX entry in standard academic format."""
        bibtex_lines = []
        bibtex_lines.append(f"@bibitem{{{cite_key},")

        if citation.get('title'):
            title = citation['title'].replace('{', '').replace('}', '')
            bibtex_lines.append(f"  title={{{title}}},")

        # Format authors
        if citation.get('authors') and len(citation['authors']) > 0:
            if isinstance(citation['authors'], list):
                author_str = " and ".join(citation['authors'])
            else:
                author_str = str(citation['authors'])
            bibtex_lines.append(f"  author={{{author_str}}},")
        else:
            bibtex_lines.append(f"  author={{Anonymous}},")

        if citation.get('journal'):
            journal = citation['journal'].replace('{', '').replace('}', '')
            bibtex_lines.append(f"  journal={{{journal}}},")

        if citation.get('volume'):
            bibtex_lines.append(f"  volume={{{citation['volume']}}},")
        else:
            bibtex_lines.append(f"  volume={{}},")

        if citation.get('number'):
            bibtex_lines.append(f"  number={{{citation['number']}}},")
        else:
            bibtex_lines.append(f"  number={{}},")

        if citation.get('pages'):
            # Format pages properly (replace - with --)
            pages = citation['pages'].replace('-', '--')
            bibtex_lines.append(f"  pages={{{pages}}},")
        else:
            bibtex_lines.append(f"  pages={{}},")

        if citation.get('year'):
            bibtex_lines.append(f"  year={{{citation['year']}}},")

        if citation.get('publisher'):
            publisher = citation['publisher'].replace('{', '').replace('}', '')
            bibtex_lines.append(f"  publisher={{{publisher}}}")
        else:
            bibtex_lines.append(f"  publisher={{}}")

        bibtex_lines.append("}")
        bibtex_lines.append("")  # Empty line

        return "\n".join(bibtex_lines)

    def create_fallback_citation(self, paper: Dict) -> Dict:
        """Create citation from CSV data when online search fails."""
        return {
            'title': paper.get('title', ''),
            'authors': ['Anonymous'],
            'journal': paper.get('venue', ''),
            'year': str(paper.get('year', '')),
            'volume': '',
            'number': '',
            'pages': '',
            'publisher': '',
            'doi': '',
            'source': 'csv_fallback'
        }

    def generate_enhanced_citations(self, csv_file_path: str, max_papers: int = None,
                                  output_format: str = 'both', use_fallback: bool = True):
        """Generate enhanced citations with complete information."""
        papers = self.read_papers_from_csv(csv_file_path)

        if not papers:
            print("No papers found to process.")
            return

        # Limit number of papers if specified
        if max_papers:
            papers = papers[:max_papers]
            print(f"Processing first {len(papers)} papers...")
        else:
            print(f"Processing all {len(papers)} papers...")

        # Create cite directory
        cite_dir = os.path.join(os.path.dirname(csv_file_path), 'cite')
        os.makedirs(cite_dir, exist_ok=True)

        timestamp = time.strftime("%Y%m%d_%H%M%S")

        successful_citations = []
        fallback_citations = []
        failed_citations = []

        for i, paper in enumerate(papers, 1):
            title = paper.get('title', '')
            print(f"\nProcessing {i}/{len(papers)}:")

            # Try to get complete citation info
            citation = self.get_complete_citation(title)

            if citation:
                successful_citations.append(citation)
            elif use_fallback:
                # Use CSV data as fallback
                fallback_citation = self.create_fallback_citation(paper)
                fallback_citations.append(fallback_citation)
                print(f"◐ Using fallback for: {title[:60]}...")
            else:
                failed_citations.append(title)
                print(f"✗ Failed: {title[:60]}...")

            # Add delay between requests
            if i < len(papers):
                time.sleep(self.delay)

        # Save all citations
        all_citations = successful_citations + fallback_citations
        self.save_enhanced_citations(all_citations, successful_citations,
                                   fallback_citations, failed_citations,
                                   cite_dir, timestamp, output_format)

        print(f"\n=== Enhanced Citation Summary ===")
        print(f"Total papers processed: {len(papers)}")
        print(f"Complete citations found: {len(successful_citations)}")
        print(f"Fallback citations used: {len(fallback_citations)}")
        print(f"Failed citations: {len(failed_citations)}")
        print(f"Overall success rate: {len(all_citations)/len(papers)*100:.1f}%")
        print(f"Complete citation rate: {len(successful_citations)/len(papers)*100:.1f}%")

    def save_enhanced_citations(self, all_citations: List[Dict], successful: List[Dict],
                              fallback: List[Dict], failed: List[str],
                              cite_dir: str, timestamp: str, output_format: str):
        """Save enhanced citations to files."""

        if output_format in ['bibtex', 'both'] and all_citations:
            # Complete citations file
            bibtex_filename = os.path.join(cite_dir, f"enhanced_citations_{timestamp}.bib")
            with open(bibtex_filename, 'w', encoding='utf-8') as f:
                f.write("% Enhanced BibTeX citations with complete information\n")
                f.write(f"% Generated on {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"% Total papers: {len(all_citations)}\n")
                f.write(f"% Complete citations: {len(successful)}\n")
                f.write(f"% Fallback citations: {len(fallback)}\n\n")

                # Write complete citations first
                if successful:
                    f.write("% Citations with complete information from online sources\n\n")
                    for i, citation in enumerate(successful, 1):
                        cite_key = f"ref{i}"
                        f.write(self.format_bibtex_entry(citation, cite_key))

                # Write fallback citations
                if fallback:
                    f.write("\n% Citations created from CSV data (fallback)\n\n")
                    start_idx = len(successful) + 1
                    for i, citation in enumerate(fallback, start_idx):
                        cite_key = f"ref{i}"
                        f.write(self.format_bibtex_entry(citation, cite_key))

            print(f"Enhanced BibTeX citations saved to: {bibtex_filename}")

        # Save failed citations for manual review
        if failed:
            failed_filename = os.path.join(cite_dir, f"failed_enhanced_citations_{timestamp}.txt")
            with open(failed_filename, 'w', encoding='utf-8') as f:
                f.write("Papers that couldn't be found with complete citation information:\n\n")
                for i, title in enumerate(failed, 1):
                    f.write(f"{i}. {title}\n")
            print(f"Failed citations saved to: {failed_filename}")

def main():
    """Main function to generate enhanced citations."""

    # Set up file paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(current_dir)
    csv_file = os.path.join(project_dir, 'results', 'consolidated_papers.csv')

    # Check if CSV file exists
    if not os.path.exists(csv_file):
        print(f"Error: Could not find consolidated_papers.csv at {csv_file}")
        return

    # Initialize enhanced citation generator
    generator = EnhancedCitationGenerator(delay=2.0)  # 2 second delay between requests

    # Generate enhanced citations
    generator.generate_enhanced_citations(
        csv_file_path=csv_file,
        max_papers=20,  # Start with 20 papers for testing
        output_format='bibtex',
        use_fallback=True
    )

if __name__ == "__main__":
    main()
