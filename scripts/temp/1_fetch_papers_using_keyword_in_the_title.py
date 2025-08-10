#!/usr/bin/env python3
"""
Research Paper Fetcher using Crossref API
Interactive tool to search for research papers by keyword and export to CSV
"""
# https://api.crossref.org/works?query.title=

import pandas as pd
import requests
import time
import os
from typing import List, Dict, Optional
from urllib.parse import quote


class CrossrefPaperFetcher:
    """
    A tool to fetch research papers from Crossref API based on keywords
    """

    def __init__(self):
        self.base_url = "https://api.crossref.org/works"
        self.headers = {
            'User-Agent': 'ResearchHelper/1.0 (mailto:researcher@example.com)'
        }
        self.papers = []

    def search_papers(self, keyword: str, additional_keyword: str, from_year: int, total_results: int) -> List[Dict]:
        """
        Search for papers using Crossref API

        Args:
            keyword: Primary search keyword/phrase
            additional_keyword: Additional keyword to include in search
            from_year: Starting year for search (to present)
            total_results: Total number of results to fetch

        Returns:
            List of paper dictionaries
        """
        papers = []
        rows_per_request = min(20, total_results)  # Crossref allows max 20 rows per request
        offset = 0
        fetched_count = 0

        # Build search query with both keywords
        if additional_keyword.strip():
            combined_query = f"{keyword} {additional_keyword}"
        else:
            combined_query = keyword

        print(f"🔍 Searching for papers with keywords: '{combined_query}'")
        print(f"📅 Year range: {from_year} to present")
        print(f"📊 Target results: {total_results}")
        print("📄 Filtering: Conference and Journal papers only")
        print("-" * 50)

        while fetched_count < total_results:
            try:
                # Calculate how many rows to fetch in this request
                remaining = total_results - fetched_count
                current_rows = min(rows_per_request, remaining)

                # Build query URL with year filter and type filter
                encoded_query = quote(combined_query)
                url = (f"{self.base_url}?query={encoded_query}"
                      f"&filter=from-pub-date:{from_year},type:journal-article,type:proceedings-article"
                      f"&rows={current_rows}&offset={offset}&sort=relevance")

                print(f"📡 Fetching papers {offset + 1} to {offset + current_rows}...")

                # Make API request
                response = requests.get(url, headers=self.headers, timeout=15)
                response.raise_for_status()

                data = response.json()
                items = data.get('message', {}).get('items', [])

                if not items:
                    print("⚠️ No more papers found")
                    break

                # Process each paper
                for idx, item in enumerate(items):
                    if fetched_count >= total_results:
                        break

                    # Additional filtering for conference and journal papers
                    paper_type = item.get('type', '')
                    if paper_type in ['journal-article', 'proceedings-article']:
                        paper = self.extract_paper_info(item, fetched_count + 1)
                        papers.append(paper)
                        fetched_count += 1

                        # Show progress
                        if (fetched_count) % 10 == 0 or fetched_count == total_results:
                            print(f"   ✅ Processed {fetched_count}/{total_results} papers")

                offset += current_rows

                # Rate limiting - be respectful to the API
                time.sleep(0.2)

            except requests.exceptions.RequestException as e:
                print(f"❌ Error fetching data: {e}")
                break
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
                break

        print(f"🎯 Successfully fetched {len(papers)} papers")
        return papers

    def extract_paper_info(self, item: Dict, paper_id: int) -> Dict:
        """
        Extract paper information from Crossref API response

        Args:
            item: Single paper item from API response
            paper_id: Sequential ID for the paper

        Returns:
            Dictionary with paper information
        """
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
        # Try multiple possible abstract field names in Crossref API
        if 'abstract' in item and item['abstract']:
            abstract = item['abstract']
        elif 'subtitle' in item and item['subtitle']:
            # Sometimes abstract is in subtitle field
            abstract = item['subtitle'][0] if isinstance(item['subtitle'], list) else item['subtitle']

        # Clean up abstract text if found
        if abstract:
            # Clean up abstract text - remove HTML tags if present
            import re
            abstract = re.sub(r'<[^>]+>', '', abstract)  # Remove HTML tags
            abstract = re.sub(r'\s+', ' ', abstract)  # Normalize whitespace
            abstract = abstract.strip()

        # Debug: Print available fields to understand the structure
        if not abstract:
            # Uncomment the line below for debugging to see what fields are available
            # print(f"Available fields for debugging: {list(item.keys())}")
            pass

        # Extract journal/container
        journal = ""
        if 'container-title' in item and item['container-title']:
            journal = item['container-title'][0] if isinstance(item['container-title'], list) else item['container-title']

        # Extract publication year
        year = ""
        if 'published-print' in item and item['published-print'].get('date-parts'):
            year = str(item['published-print']['date-parts'][0][0])
        elif 'published-online' in item and item['published-online'].get('date-parts'):
            year = str(item['published-online']['date-parts'][0][0])

        # Extract other fields
        volume = item.get('volume', '')
        issue = item.get('issue', '')
        pages = item.get('page', '')
        publisher = item.get('publisher', '')
        doi = item.get('DOI', '')
        url = item.get('URL', '')
        paper_type = item.get('type', '')

        return {
            'paper_id': f"paper_{paper_id:03d}",
            'title': title,
            'abstract': abstract,
            'authors': '; '.join(authors) if authors else 'Not Available',
            'journal': journal,
            'year': year,
            'volume': volume,
            'issue': issue,
            'pages': pages,
            'publisher': publisher,
            'doi': doi,
            'url': url,
            'type': paper_type
        }

    def save_to_csv(self, papers: List[Dict], keyword: str, output_dir: str = None) -> str:
        """
        Save papers to CSV file

        Args:
            papers: List of paper dictionaries
            keyword: Search keyword used (for filename)
            output_dir: Output directory (defaults to results/new folder)

        Returns:
            Path to saved CSV file
        """
        if not papers:
            print("⚠️ No papers to save")
            return ""

        # Set default output directory to results/new
        if output_dir is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_dir = os.path.dirname(current_dir)
            output_dir = os.path.join(project_dir, 'results', 'new')

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Create DataFrame
        df = pd.DataFrame(papers)

        # Generate filename
        safe_keyword = "".join(c for c in keyword if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_keyword = safe_keyword.replace(' ', '_').lower()
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"crossref_papers_{safe_keyword}_{timestamp}.csv"
        filepath = os.path.join(output_dir, filename)

        # Save to CSV
        df.to_csv(filepath, index=False)

        return filepath

    def display_summary(self, papers: List[Dict]):
        """
        Display summary of fetched papers

        Args:
            papers: List of paper dictionaries
        """
        if not papers:
            return

        print(f"\n📊 SUMMARY OF FETCHED PAPERS")
        print("=" * 50)
        print(f"Total papers: {len(papers)}")

        # Count by year
        years = [p['year'] for p in papers if p['year']]
        if years:
            year_counts = {}
            for year in years:
                year_counts[year] = year_counts.get(year, 0) + 1

            print(f"\nPapers by year:")
            for year in sorted(year_counts.keys(), reverse=True)[:5]:
                print(f"  {year}: {year_counts[year]} papers")

        # Count by type
        types = [p['type'] for p in papers if p['type']]
        if types:
            type_counts = {}
            for paper_type in types:
                type_counts[paper_type] = type_counts.get(paper_type, 0) + 1

            print(f"\nPapers by type:")
            for paper_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"  {paper_type}: {count} papers")

        print(f"\n📄 SAMPLE PAPERS:")
        print("-" * 50)
        for i, paper in enumerate(papers[:3]):
            print(f"{i+1}. {paper['title'][:60]}...")
            print(f"   Authors: {paper['authors'][:50]}...")
            print(f"   Journal: {paper['journal']}")
            print(f"   Year: {paper['year']}")
            print()


def get_user_input():
    """
    Get keyword and number of results from user

    Returns:
        Tuple of (keyword, total_results)
    """
    print("🔬 Research Paper Fetcher using Crossref API")
    print("=" * 50)

    # Get keyword
    while True:
        keyword = input("📝 Enter search keyword or phrase: ").strip()
        if keyword:
            break
        print("❌ Please enter a valid keyword")

    # Get additional keyword (optional)
    additional_keyword = input("➕ Enter additional keyword (optional): ").strip()

    # Get year filter
    while True:
        try:
            from_year = int(input("📅 Enter starting year for search (e.g., 2020): "))
            if from_year > 0:
                break
            print("❌ Please enter a valid year")
        except ValueError:
            print("❌ Please enter a valid year")

    # Get number of results
    while True:
        try:
            total_results = int(input("📊 Enter number of results to fetch (1-1000): "))
            if 1 <= total_results <= 1000:
                break
            print("❌ Please enter a number between 1 and 1000")
        except ValueError:
            print("❌ Please enter a valid number")

    return keyword, additional_keyword, from_year, total_results


def main():
    """
    Main function to run the research paper fetcher
    """
    try:
        # Get user input
        keyword, additional_keyword, from_year, total_results = get_user_input()

        # Initialize fetcher
        fetcher = CrossrefPaperFetcher()

        # Search for papers
        papers = fetcher.search_papers(keyword, additional_keyword, from_year, total_results)

        if papers:
            # Save to CSV
            csv_file = fetcher.save_to_csv(papers, keyword)

            # Display summary
            fetcher.display_summary(papers)

            print(f"\n💾 Results saved to: {csv_file}")
            print(f"📁 File contains {len(papers)} papers with the following columns:")
            print("   paper_id, title, abstract, authors, journal, year, volume, issue, pages, publisher, doi, url, type")

        else:
            print("❌ No papers found for the given keyword")

    except KeyboardInterrupt:
        print("\n\n⏹️ Operation cancelled by user")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")


if __name__ == "__main__":
    main()
