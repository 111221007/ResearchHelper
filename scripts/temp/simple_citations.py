#!/usr/bin/env python3
"""
Crossref API Citation Generator
Generates BibTeX citations using only titles from CSV and all metadata from Crossref API.
"""

import pandas as pd
import os
import time
import re
import requests
import json
from typing import Dict, Optional
from urllib.parse import quote


def search_crossref(title: str) -> Optional[Dict]:
    """Search for paper metadata using Crossref API."""
    try:
        # Clean and encode the title for the API call
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
                'type': work.get('type', 'article'),
                'url': work.get('URL', ''),
                'isbn': work.get('ISBN', []),
                'issn': work.get('ISSN', [])
            }

            return result

    except Exception as e:
        print(f"  ❌ Error searching Crossref: {str(e)}")
        return None

    return None


def clean_title(title: str) -> str:
    """Clean title for BibTeX format."""
    title = re.sub(r'[{}]', '', title)
    return title.strip()


def generate_cite_key(title: str, year: str, ref_number: int) -> str:
    """Generate citation key based on first author and year or use ref format."""
    return f"ref{ref_number}"


def create_bibtex_entry_from_crossref(crossref_data: Dict, ref_number: int) -> str:
    """Create a BibTeX entry from Crossref API response."""
    cite_key = generate_cite_key(crossref_data.get('title', ''), crossref_data.get('year', ''), ref_number)

    title = clean_title(crossref_data.get('title', ''))
    authors = crossref_data.get('authors', [])
    journal = crossref_data.get('journal', '')
    publisher = crossref_data.get('publisher', '')
    year = crossref_data.get('year', '')
    volume = crossref_data.get('volume', '')
    issue = crossref_data.get('issue', '')
    pages = crossref_data.get('pages', '')
    doi = crossref_data.get('doi', '')
    work_type = crossref_data.get('type', 'article')

    # Determine BibTeX entry type
    entry_type = 'article'
    if 'proceedings' in work_type or 'conference' in work_type:
        entry_type = 'inproceedings'
    elif 'book' in work_type:
        entry_type = 'book'
    elif 'chapter' in work_type:
        entry_type = 'incollection'

    # Format authors
    if authors:
        author_str = " and ".join(authors)
    else:
        author_str = "Anonymous"

    # Format pages
    if pages:
        pages = pages.replace('-', '--')  # Use en-dash for page ranges

    bibtex = f"@{entry_type}{{{cite_key},\n"
    bibtex += f"  title={{{title}}},\n"
    bibtex += f"  author={{{author_str}}},\n"

    if entry_type == 'inproceedings':
        bibtex += f"  booktitle={{{journal}}},\n"
    elif entry_type == 'article':
        bibtex += f"  journal={{{journal}}},\n"
    else:
        bibtex += f"  title={{{title}}},\n"

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
        # Remove trailing comma
        bibtex = bibtex.rstrip(',\n') + '\n'

    bibtex += "}\n\n"
    return bibtex


def create_ris_entry(crossref_data: Dict) -> str:
    """Create a RIS entry from Crossref API response."""
    title = crossref_data.get('title', '')
    authors = crossref_data.get('authors', [])
    journal = crossref_data.get('journal', '')
    publisher = crossref_data.get('publisher', '')
    year = crossref_data.get('year', '')
    volume = crossref_data.get('volume', '')
    issue = crossref_data.get('issue', '')
    pages = crossref_data.get('pages', '')
    doi = crossref_data.get('doi', '')
    work_type = crossref_data.get('type', 'article')

    # Determine RIS entry type
    entry_type = 'JOUR'  # Journal article
    if 'proceedings' in work_type or 'conference' in work_type:
        entry_type = 'CONF'  # Conference paper
    elif 'book' in work_type:
        entry_type = 'BOOK'
    elif 'chapter' in work_type:
        entry_type = 'CHAP'

    ris = f"TY  - {entry_type}\n"

    if title:
        ris += f"TI  - {title}\n"

    # Format authors
    for author in authors:
        ris += f"AU  - {author}\n"

    if journal:
        if entry_type == 'CONF':
            ris += f"T2  - {journal}\n"
        else:
            ris += f"JO  - {journal}\n"

    if year:
        ris += f"PY  - {year}\n"

    if volume:
        ris += f"VL  - {volume}\n"

    if issue:
        ris += f"IS  - {issue}\n"

    if pages:
        ris += f"SP  - {pages}\n"

    if publisher:
        ris += f"PB  - {publisher}\n"

    if doi:
        ris += f"DO  - {doi}\n"

    ris += "ER  - \n\n"
    return ris


def create_fallback_bibtex_entry(title: str, ref_number: int) -> str:
    """Create a minimal BibTeX entry when Crossref fails."""
    cite_key = f"ref{ref_number}"
    clean_title_str = clean_title(title)

    bibtex = f"@misc{{{cite_key},\n"
    bibtex += f"  title={{{clean_title_str}}},\n"
    bibtex += f"  author={{Anonymous}},\n"
    bibtex += f"  year={{2024}},\n"
    bibtex += f"  note={{Metadata not available from Crossref}}\n"
    bibtex += "}\n\n"
    return bibtex


def create_fallback_ris_entry(title: str) -> str:
    """Create a minimal RIS entry when Crossref fails."""
    clean_title_str = clean_title(title)

    ris = f"TY  - MISC\n"
    ris += f"TI  - {clean_title_str}\n"
    ris += f"AU  - Anonymous\n"
    ris += f"PY  - 2024\n"
    ris += f"N1  - Metadata not available from Crossref\n"
    ris += "ER  - \n\n"
    return ris


def main():
    """Main function."""
    print("🚀 Starting Crossref API citation generator...")
    print("📡 Using only titles from CSV, fetching all metadata from Crossref API...")

    # Set up file paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(current_dir)
    csv_file = os.path.join(project_dir, 'results', 'consolidated_papers.csv')
    output_dir = os.path.join(project_dir, 'results', 'cite')

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Check if CSV file exists
    if not os.path.exists(csv_file):
        print(f"❌ Error: Could not find consolidated_papers.csv at {csv_file}")
        return

    # Read CSV file
    try:
        df = pd.read_csv(csv_file)
        print(f"📖 Found {len(df)} papers in CSV file")
    except Exception as e:
        print(f"❌ Error reading CSV file: {e}")
        return

    # Generate timestamp for filenames
    timestamp = time.strftime("%Y%m%d_%H%M%S")

    print("📝 Generating BibTeX citations using Crossref API...")
    print("⏱️ This may take a few minutes due to API rate limiting...")

    # Track statistics
    crossref_hits = 0
    crossref_misses = 0

    # Generate BibTeX file
    bibtex_filename = os.path.join(output_dir, f"crossref_citations_{timestamp}.bib")
    with open(bibtex_filename, 'w', encoding='utf-8') as f:
        f.write("% Bibliography for Serverless Computing Research Papers\n")
        f.write("% Generated using Crossref API for accurate metadata\n")
        f.write(f"% Generated on {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"% Total papers: {len(df)}\n\n")

        for idx, (_, row) in enumerate(df.iterrows(), 1):
            title = row.get('title', '')
            if not title:
                print(f"  ⚠️ Paper {idx}: No title found, skipping...")
                continue

            print(f"Processing {idx}/{len(df)}: {title[:60]}...")

            # Fetch metadata from Crossref
            crossref_data = search_crossref(title)

            if crossref_data:
                print(f"  ✅ Found Crossref data")
                crossref_hits += 1
                bibtex_entry = create_bibtex_entry_from_crossref(crossref_data, idx)
            else:
                print(f"  ❌ No Crossref data found, using fallback")
                crossref_misses += 1
                bibtex_entry = create_fallback_bibtex_entry(title, idx)

            f.write(bibtex_entry)

            # Add delay to be respectful to the API
            if idx < len(df):
                time.sleep(0.2)  # 200ms delay between requests

            # Progress indicator
            if idx % 10 == 0 or idx == len(df):
                print(f"  📊 Progress: {idx}/{len(df)} papers processed")

    print("📋 Generating RIS citations...")

    # Generate RIS file
    ris_filename = os.path.join(output_dir, f"crossref_citations_{timestamp}.ris")
    with open(ris_filename, 'w', encoding='utf-8') as f:
        f.write("Provider: Research Helper via Crossref API\n")
        f.write("Database: Serverless Computing Papers\n")
        f.write(f"Content: Bibliography ({len(df)} papers)\n\n")

        for idx, (_, row) in enumerate(df.iterrows(), 1):
            title = row.get('title', '')
            if not title:
                continue

            # Fetch metadata from Crossref (reuse from BibTeX generation)
            crossref_data = search_crossref(title)

            if crossref_data:
                ris_entry = create_ris_entry(crossref_data)
            else:
                ris_entry = create_fallback_ris_entry(title)

            f.write(ris_entry)

            # Add delay
            if idx < len(df):
                time.sleep(0.2)

    print("📊 Generating summary report...")

    # Generate summary report
    summary_filename = os.path.join(output_dir, f"crossref_summary_{timestamp}.txt")
    with open(summary_filename, 'w', encoding='utf-8') as f:
        f.write("Crossref API Citation Generation Summary\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Total papers processed: {len(df)}\n")
        f.write(f"BibTeX file: {os.path.basename(bibtex_filename)}\n")
        f.write(f"RIS file: {os.path.basename(ris_filename)}\n")
        f.write(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("Crossref API Results:\n")
        f.write("-" * 20 + "\n")
        f.write(f"Successful metadata retrieval: {crossref_hits} papers\n")
        f.write(f"Fallback entries (no Crossref data): {crossref_misses} papers\n")
        if crossref_hits + crossref_misses > 0:
            success_rate = crossref_hits / (crossref_hits + crossref_misses) * 100
            f.write(f"Success rate: {success_rate:.1f}%\n\n")

        f.write(f"Citation keys: ref1 to ref{len(df)}\n")
        f.write("\nNote: All metadata (authors, journal, volume, etc.) comes from Crossref API\n")
        f.write("Only paper titles were used from the original CSV file\n\n")
        f.write("Example BibTeX format:\n")
        f.write("@article{ref1,\n")
        f.write("  title={Actual Paper Title from Crossref},\n")
        f.write("  author={Real Author Names from Crossref},\n")
        f.write("  journal={Actual Journal Name},\n")
        f.write("  volume={12},\n")
        f.write("  number={3},\n")
        f.write("  pages={123--145},\n")
        f.write("  year={2024},\n")
        f.write("  publisher={Real Publisher}\n")
        f.write("}\n\n")
        f.write("To cite in LaTeX: \\cite{ref1}, \\cite{ref2}, etc.\n")

    print(f"\n🎉 Success! Generated Crossref-based citations:")
    print(f"📄 BibTeX: {os.path.basename(bibtex_filename)}")
    print(f"📄 RIS: {os.path.basename(ris_filename)}")
    print(f"📊 Summary: {os.path.basename(summary_filename)}")
    print(f"📁 All files saved in: results/cite/")
    print(f"\n📈 Crossref API Results:")
    print(f"   ✅ Enhanced metadata: {crossref_hits} papers")
    print(f"   ❌ Fallback entries: {crossref_misses} papers")
    if crossref_hits + crossref_misses > 0:
        success_rate = crossref_hits / (crossref_hits + crossref_misses) * 100
        print(f"   📊 Success rate: {success_rate:.1f}%")
    print(f"\n🔗 Citation format: ref1, ref2, ..., ref{len(df)}")
    print("🎯 Ready for academic use with real metadata from Crossref!")
