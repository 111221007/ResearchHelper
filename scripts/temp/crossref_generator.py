#!/usr/bin/env python3
"""
Crossref Citation Generator - Final Version
Uses only titles from CSV, fetches all metadata from Crossref API
"""

import pandas as pd
import os
import time
import re
import requests
from typing import Dict, Optional
from urllib.parse import quote


def search_crossref(title: str) -> Optional[Dict]:
    """Search Crossref API for paper metadata."""
    try:
        clean_title = re.sub(r'[^\w\s]', ' ', title).strip()
        encoded_title = quote(clean_title)
        url = f"https://api.crossref.org/works?query.title={encoded_title}&rows=1"

        headers = {'User-Agent': 'ResearchHelper/1.0 (mailto:researcher@example.com)'}
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

            return {
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
    except Exception as e:
        print(f"    Error: {str(e)}")
        return None
    return None


def create_bibtex_from_crossref(data: Dict, ref_num: int) -> str:
    """Create BibTeX entry from Crossref data."""
    cite_key = f"ref{ref_num}"
    title = data.get('title', '').replace('{', '').replace('}', '')
    authors = " and ".join(data.get('authors', [])) or "Anonymous"
    journal = data.get('journal', '')
    publisher = data.get('publisher', '')
    year = data.get('year', '')
    volume = data.get('volume', '')
    issue = data.get('issue', '')
    pages = data.get('pages', '').replace('-', '--') if data.get('pages') else ''
    doi = data.get('doi', '')

    bibtex = f"@article{{{cite_key},\n"
    bibtex += f"  title={{{title}}},\n"
    bibtex += f"  author={{{authors}}},\n"
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


def create_fallback_bibtex(title: str, ref_num: int) -> str:
    """Fallback BibTeX when Crossref fails."""
    cite_key = f"ref{ref_num}"
    clean_title = title.replace('{', '').replace('}', '')

    return f"""@misc{{{cite_key},
  title={{{clean_title}}},
  author={{Anonymous}},
  year={{2024}},
  note={{Crossref metadata not available}}
}}

"""


def main():
    print("🚀 Starting Crossref API Citation Generator")
    print("📡 Fetching real academic metadata from Crossref...")

    # Setup paths
    csv_file = "/results/consolidated_papers.csv"
    output_dir = "/results/cite"
    os.makedirs(output_dir, exist_ok=True)

    # Read CSV
    df = pd.read_csv(csv_file)
    print(f"📖 Processing {len(df)} papers from CSV")

    # Generate timestamp
    timestamp = time.strftime("%Y%m%d_%H%M%S")

    # Output files
    bibtex_file = os.path.join(output_dir, f"crossref_citations_{timestamp}.bib")

    crossref_hits = 0
    crossref_misses = 0

    print("📝 Generating BibTeX citations...")

    with open(bibtex_file, 'w', encoding='utf-8') as f:
        f.write("% Serverless Computing Research Papers - Crossref API Generated\n")
        f.write(f"% Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"% Total papers: {len(df)}\n\n")

        for idx, (_, row) in enumerate(df.iterrows(), 1):
            title = row.get('title', '')
            print(f"[{idx:3d}/{len(df)}] {title[:50]}...")

            # Fetch from Crossref
            crossref_data = search_crossref(title)

            if crossref_data:
                print(f"    ✅ Found: {crossref_data.get('journal', 'Unknown Journal')}")
                crossref_hits += 1
                bibtex_entry = create_bibtex_from_crossref(crossref_data, idx)
            else:
                print(f"    ❌ Not found - using fallback")
                crossref_misses += 1
                bibtex_entry = create_fallback_bibtex(title, idx)

            f.write(bibtex_entry)

            # Rate limiting
            if idx < len(df):
                time.sleep(0.3)

            # Progress updates
            if idx % 25 == 0:
                success_rate = crossref_hits / (crossref_hits + crossref_misses) * 100
                print(f"    📊 Progress: {idx}/{len(df)} papers | Success rate: {success_rate:.1f}%")

    # Final summary
    success_rate = crossref_hits / (crossref_hits + crossref_misses) * 100 if (crossref_hits + crossref_misses) > 0 else 0

    print(f"\n🎉 COMPLETED!")
    print(f"📄 BibTeX file: {os.path.basename(bibtex_file)}")
    print(f"📊 Results:")
    print(f"   ✅ Crossref metadata found: {crossref_hits} papers")
    print(f"   ❌ Fallback entries: {crossref_misses} papers")
    print(f"   📈 Success rate: {success_rate:.1f}%")
    print(f"\n🔗 Citations ready: ref1, ref2, ..., ref{len(df)}")
    print(f"📁 Saved to: results/cite/")


if __name__ == "__main__":
    main()
