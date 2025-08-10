#!/usr/bin/env python3
"""
Crossref API Test - Process first 5 papers only
"""

import pandas as pd
import os
import time
import re
import requests
from typing import Dict, Optional
from urllib.parse import quote


def search_crossref(title: str) -> Optional[Dict]:
    """Search for paper metadata using Crossref API."""
    try:
        clean_title = re.sub(r'[^\w\s]', ' ', title).strip()
        encoded_title = quote(clean_title)

        url = f"https://api.crossref.org/works?query.title={encoded_title}&rows=1"

        headers = {
            'User-Agent': 'ResearchHelper/1.0 (mailto:researcher@example.com)'
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()

        if data['message']['items']:
            work = data['message']['items'][0]

            # Extract authors
            authors = []
            if 'author' in work:
                for author in work['author']:
                    if 'given' in author and 'family' in author:
                        authors.append(f"{author['family']}, {author['given']}")
                    elif 'family' in author:
                        authors.append(author['family'])

            # Extract publication info
            result = {
                'title': work.get('title', [title])[0] if work.get('title') else title,
                'authors': authors,
                'journal': work.get('container-title', [''])[0] if work.get('container-title') else '',
                'publisher': work.get('publisher', ''),
                'year': str(work.get('published-print', {}).get('date-parts', [['']])[0][0] or
                           work.get('published-online', {}).get('date-parts', [['']])[0][0] or ''),
                'volume': work.get('volume', ''),
                'issue': work.get('issue', ''),
                'pages': work.get('page', ''),
                'doi': work.get('DOI', ''),
                'type': work.get('type', 'article')
            }

            return result

    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        return None

    return None


def create_bibtex_entry(crossref_data: Dict, ref_number: int) -> str:
    """Create BibTeX entry from Crossref data."""
    cite_key = f"ref{ref_number}"

    title = crossref_data.get('title', '')
    authors = crossref_data.get('authors', [])
    journal = crossref_data.get('journal', '')
    publisher = crossref_data.get('publisher', '')
    year = crossref_data.get('year', '')
    volume = crossref_data.get('volume', '')
    issue = crossref_data.get('issue', '')
    pages = crossref_data.get('pages', '')
    doi = crossref_data.get('doi', '')

    # Format authors
    author_str = " and ".join(authors) if authors else "Anonymous"

    # Format pages with en-dash
    if pages:
        pages = pages.replace('-', '--')

    bibtex = f"@article{{{cite_key},\n"
    bibtex += f"  title={{{title}}},\n"
    bibtex += f"  author={{{author_str}}},\n"
    bibtex += f"  journal={{{journal}}},\n"

    if volume:
        bibtex += f"  volume={{{volume}}},\n"

    if issue:
        bibtex += f"  number={{{issue}}},\n"

    if pages:
        bibtex += f"  pages={{{pages}}},\n"

    if year:
        bibtex += f"  year={{{year}}},\n"

    if publisher:
        bibtex += f"  publisher={{{publisher}}},\n"

    if doi:
        bibtex += f"  doi={{{doi}}}\n"
    else:
        bibtex = bibtex.rstrip(',\n') + '\n'

    bibtex += "}\n\n"
    return bibtex


def main():
    """Test with first 5 papers."""
    print("🧪 Testing Crossref API with first 5 papers...")

    # Read CSV
    csv_file = "/results/consolidated_papers.csv"
    df = pd.read_csv(csv_file)

    # Process first 5 papers
    for idx in range(min(5, len(df))):
        row = df.iloc[idx]
        title = row.get('title', '')

        print(f"\n📄 Paper {idx+1}: {title[:60]}...")

        # Search Crossref
        crossref_data = search_crossref(title)

        if crossref_data:
            print(f"  ✅ Found Crossref data!")
            print(f"  📖 Title: {crossref_data.get('title', 'N/A')}")
            print(f"  👥 Authors: {', '.join(crossref_data.get('authors', ['N/A']))}")
            print(f"  📚 Journal: {crossref_data.get('journal', 'N/A')}")
            print(f"  📅 Year: {crossref_data.get('year', 'N/A')}")
            print(f"  📊 Volume: {crossref_data.get('volume', 'N/A')}")
            print(f"  🏢 Publisher: {crossref_data.get('publisher', 'N/A')}")

            # Generate BibTeX
            bibtex = create_bibtex_entry(crossref_data, idx+1)
            print(f"  📝 BibTeX preview:")
            print("  " + "\n  ".join(bibtex.split('\n')[:8]))  # Show first 8 lines
        else:
            print(f"  ❌ No Crossref data found")

        time.sleep(1)  # Rate limiting


if __name__ == "__main__":
    main()
