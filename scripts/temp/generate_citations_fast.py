#!/usr/bin/env python3
"""
Fast Citation Generator with Crossref API
Generates BibTeX and RIS citations using Crossref API for accurate metadata.
"""

import pandas as pd
import os
import time
import re
import requests
import json
from typing import List, Dict, Optional
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
                        authors.append(f"{author['given']} {author['family']}")
                    elif 'family' in author:
                        authors.append(author['family'])

            # Extract publication info
            result = {
                'title': work.get('title', [title])[0] if work.get('title') else title,
                'authors': authors if authors else ['Anonymous'],
                'journal': work.get('container-title', [''])[0] if work.get('container-title') else '',
                'publisher': work.get('publisher', ''),
                'year': str(work.get('published-print', {}).get('date-parts', [['']])[0][0] or
                           work.get('published-online', {}).get('date-parts', [['']])[0][0] or ''),
                'volume': work.get('volume', ''),
                'issue': work.get('issue', ''),
                'pages': work.get('page', ''),
                'doi': work.get('DOI', ''),
                'type': work.get('type', 'article'),
                'url': work.get('URL', '')
            }

            return result

    except Exception as e:
        print(f"Error searching Crossref for '{title[:50]}...': {str(e)}")
        return None

    return None


def clean_title(title: str) -> str:
    """Clean title for BibTeX format."""
    # Remove special characters that might break BibTeX
    title = re.sub(r'[{}]', '', title)
    return title.strip()


def clean_author(author: str) -> str:
    """Clean author name for BibTeX format."""
    if not author or author.lower() == 'anonymous':
        return 'Anonymous'
    return author.strip()


def clean_venue(venue: str) -> str:
    """Clean venue name for BibTeX format."""
    if not venue:
        return 'Unknown Venue'
    # Remove common prefixes
    venue = re.sub(r'^(Proceedings of|Proc\.?|Conference on|International|IEEE|ACM)\s*', '', venue, flags=re.IGNORECASE)
    return venue.strip()


def generate_cite_key(index: int) -> str:
    """Generate citation key in ref format."""
    return f"ref{index}"


def create_bibtex_entry(paper: Dict, ref_number: int, crossref_data: Optional[Dict] = None) -> str:
    """Create a BibTeX entry from paper data and Crossref metadata."""
    cite_key = generate_cite_key(ref_number)

    # Use Crossref data if available, otherwise fall back to CSV data
    if crossref_data:
        title = clean_title(crossref_data.get('title', paper.get('title', '')))
        authors = crossref_data.get('authors', [paper.get('authors', 'Anonymous')])
        venue = crossref_data.get('journal', paper.get('venue', ''))
        year = crossref_data.get('year', str(paper.get('year', '')))
        volume = crossref_data.get('volume', '')
        issue = crossref_data.get('issue', '')
        pages = crossref_data.get('pages', '')
        doi = crossref_data.get('doi', '')
        entry_type_hint = crossref_data.get('type', '')
    else:
        title = clean_title(paper.get('title', ''))
        authors = [clean_author(paper.get('authors', 'Anonymous'))]
        venue = clean_venue(paper.get('venue', ''))
        year = str(paper.get('year', ''))
        volume = ''
        issue = ''
        pages = ''
        doi = ''
        entry_type_hint = ''

    # Format authors
    if isinstance(authors, list):
        author_str = " and ".join(authors)
    else:
        author_str = str(authors)

    # Determine entry type
    entry_type = 'article'
    if entry_type_hint:
        if 'proceedings' in entry_type_hint or 'conference' in entry_type_hint:
            entry_type = 'inproceedings'
    elif any(word in venue.lower() for word in ['conference', 'proceedings', 'workshop', 'symposium']):
        entry_type = 'inproceedings'
    elif any(word in venue.lower() for word in ['arxiv', 'preprint']):
        entry_type = 'misc'

    bibtex = f"@{entry_type}{{{cite_key},\n"
    bibtex += f"  title={{{title}}},\n"
    bibtex += f"  author={{{author_str}}},\n"

    if entry_type == 'inproceedings':
        bibtex += f"  booktitle={{{venue}}},\n"
    elif entry_type == 'article':
        bibtex += f"  journal={{{venue}}},\n"
    else:
        bibtex += f"  howpublished={{{venue}}},\n"

    if year:
        bibtex += f"  year={{{year}}},\n"

    if volume:
        bibtex += f"  volume={{{volume}}},\n"

    if issue:
        bibtex += f"  number={{{issue}}},\n"

    if pages:
        bibtex += f"  pages={{{pages}}},\n"

    if doi:
        bibtex += f"  doi={{{doi}}},\n"

    # Add category and keywords from original data
    category = paper.get('category', '')
    keywords = paper.get('keywords', '')

    if category:
        bibtex += f"  note={{Category: {category}}},\n"

    if keywords:
        bibtex += f"  keywords={{{keywords}}}\n"
    else:
        # Remove trailing comma
        bibtex = bibtex.rstrip(',\n') + '\n'

    bibtex += "}\n\n"

    return bibtex


def create_ris_entry(paper: Dict, crossref_data: Optional[Dict] = None) -> str:
    """Create a RIS entry from paper data and Crossref metadata."""
    # Use Crossref data if available, otherwise fall back to CSV data
    if crossref_data:
        title = crossref_data.get('title', paper.get('title', ''))
        authors = crossref_data.get('authors', [paper.get('authors', 'Anonymous')])
        venue = crossref_data.get('journal', paper.get('venue', ''))
        year = crossref_data.get('year', str(paper.get('year', '')))
        volume = crossref_data.get('volume', '')
        issue = crossref_data.get('issue', '')
        pages = crossref_data.get('pages', '')
        doi = crossref_data.get('doi', '')
        entry_type_hint = crossref_data.get('type', '')
    else:
        title = paper.get('title', '')
        authors = [clean_author(paper.get('authors', 'Anonymous'))]
        venue = clean_venue(paper.get('venue', ''))
        year = str(paper.get('year', ''))
        volume = ''
        issue = ''
        pages = ''
        doi = ''
        entry_type_hint = ''

    # Determine entry type
    entry_type = 'JOUR'  # Journal article
    if entry_type_hint:
        if 'proceedings' in entry_type_hint or 'conference' in entry_type_hint:
            entry_type = 'CONF'
    elif any(word in venue.lower() for word in ['conference', 'proceedings', 'workshop', 'symposium']):
        entry_type = 'CONF'  # Conference paper
    elif any(word in venue.lower() for word in ['arxiv', 'preprint']):
        entry_type = 'UNPB'  # Unpublished

    ris = f"TY  - {entry_type}\n"

    if title:
        ris += f"TI  - {title}\n"

    # Format authors
    if isinstance(authors, list):
        for author in authors:
            ris += f"AU  - {author}\n"
    else:
        ris += f"AU  - {authors}\n"

    if venue:
        if entry_type == 'CONF':
            ris += f"T2  - {venue}\n"
        else:
            ris += f"JO  - {venue}\n"

    if year:
        ris += f"PY  - {year}\n"

    if volume:
        ris += f"VL  - {volume}\n"

    if issue:
        ris += f"IS  - {issue}\n"

    if pages:
        ris += f"SP  - {pages}\n"

    if doi:
        ris += f"DO  - {doi}\n"

    # Add category and keywords from original data
    category = paper.get('category', '')
    keywords = paper.get('keywords', '')

    if category:
        ris += f"KW  - {category}\n"

    if keywords:
        ris += f"AB  - Keywords: {keywords}\n"

    ris += "ER  - \n\n"

    return ris


def generate_citations_from_csv(csv_file_path: str, output_dir: str = None, use_crossref: bool = True):
    """Generate citations from CSV file with optional Crossref API integration."""

    if output_dir is None:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(current_dir)
        output_dir = os.path.join(project_dir, 'results', 'cite')

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Read CSV file
    try:
        df = pd.read_csv(csv_file_path)
        print(f"Found {len(df)} papers in CSV file")
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return

    # Generate timestamp for filenames
    timestamp = time.strftime("%Y%m%d_%H%M%S")

    # Track Crossref hits and misses
    crossref_hits = 0
    crossref_misses = 0

    # Generate BibTeX file
    bibtex_filename = os.path.join(output_dir, f"all_papers_citations_{timestamp}.bib")
    with open(bibtex_filename, 'w', encoding='utf-8') as f:
        f.write("% Bibliography for Serverless Computing Research Papers\n")
        f.write(f"% Generated on {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"% Total papers: {len(df)}\n")
        f.write("% Using Crossref API for enhanced metadata\n\n")

        for idx, (_, row) in enumerate(df.iterrows(), 1):
            paper_data = {
                'title': row.get('title', ''),
                'authors': row.get('authors', 'Anonymous'),
                'venue': row.get('venue', ''),
                'year': row.get('year', ''),
                'category': row.get('category', ''),
                'keywords': row.get('keywords', '')
            }

            print(f"Processing {idx}/{len(df)}: {paper_data['title'][:60]}...")

            # Fetch metadata from Crossref
            crossref_metadata = None
            if use_crossref:
                crossref_metadata = search_crossref(paper_data['title'])
                if crossref_metadata:
                    crossref_hits += 1
                    print(f"  ✓ Found Crossref data")
                else:
                    crossref_misses += 1
                    print(f"  ◐ Using CSV data")

                # Add small delay to be respectful to the API
                time.sleep(0.1)

            bibtex_entry = create_bibtex_entry(paper_data, idx, crossref_metadata)
            f.write(bibtex_entry)

    print(f"BibTeX citations saved to: {bibtex_filename}")

    # Generate RIS file
    ris_filename = os.path.join(output_dir, f"all_papers_citations_{timestamp}.ris")
    with open(ris_filename, 'w', encoding='utf-8') as f:
        f.write("Provider: Research Helper\n")
        f.write("Database: Serverless Computing Papers\n")
        f.write(f"Content: Bibliography ({len(df)} papers)\n\n")

        for idx, (_, row) in enumerate(df.iterrows(), 1):
            paper_data = {
                'title': row.get('title', ''),
                'authors': row.get('authors', 'Anonymous'),
                'venue': row.get('venue', ''),
                'year': row.get('year', ''),
                'category': row.get('category', ''),
                'keywords': row.get('keywords', '')
            }

            # For RIS, we'll reuse the Crossref data if we have it
            crossref_metadata = None
            if use_crossref:
                crossref_metadata = search_crossref(paper_data['title'])
                time.sleep(0.1)

            ris_entry = create_ris_entry(paper_data, crossref_metadata)
            f.write(ris_entry)

    print(f"RIS citations saved to: {ris_filename}")

    # Generate summary report
    summary_filename = os.path.join(output_dir, f"citation_summary_{timestamp}.txt")
    with open(summary_filename, 'w', encoding='utf-8') as f:
        f.write("Citation Generation Summary\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Total papers processed: {len(df)}\n")
        f.write(f"BibTeX file: {os.path.basename(bibtex_filename)}\n")
        f.write(f"RIS file: {os.path.basename(ris_filename)}\n")
        f.write(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        if use_crossref:
            f.write("Crossref API Results:\n")
            f.write("-" * 20 + "\n")
            f.write(f"Successful metadata retrieval: {crossref_hits} papers\n")
            f.write(f"Fallback to CSV data: {crossref_misses} papers\n")
            f.write(f"Success rate: {crossref_hits/(crossref_hits+crossref_misses)*100:.1f}%\n\n")

        # Category breakdown
        if 'category' in df.columns:
            category_counts = df['category'].value_counts()
            f.write("Papers by category:\n")
            f.write("-" * 20 + "\n")
            for category, count in category_counts.items():
                f.write(f"{category}: {count} papers\n")

        f.write(f"\nCitation keys: ref1 to ref{len(df)}\n")
        f.write("\nBibTeX Format Examples:\n")
        f.write("@article{ref1,\n")
        f.write("  title={Paper Title},\n")
        f.write("  author={Author Name},\n")
        f.write("  journal={Venue Name},\n")
        f.write("  year={2024}\n")
        f.write("}\n\n")
        f.write("To cite in LaTeX: \\cite{ref1}, \\cite{ref2}, etc.\n")

    print(f"Summary report saved to: {summary_filename}")

    return {
        'bibtex_file': bibtex_filename,
        'ris_file': ris_filename,
        'summary_file': summary_filename,
        'total_papers': len(df),
        'crossref_hits': crossref_hits,
        'crossref_misses': crossref_misses
    }


def main():
    """Main function."""
    # Set up file paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(current_dir)
    csv_file = os.path.join(project_dir, 'results', 'consolidated_papers.csv')

    # Check if CSV file exists
    if not os.path.exists(csv_file):
        print(f"Error: Could not find consolidated_papers.csv at {csv_file}")
        return

    print("Generating citations from consolidated papers using Crossref API...")
    print("This will take a few minutes to process all papers...\n")

    result = generate_citations_from_csv(csv_file, use_crossref=True)

    if result:
        print(f"\n🎉 Success! Generated citations for {result['total_papers']} papers:")
        print(f"📄 BibTeX: {os.path.basename(result['bibtex_file'])}")
        print(f"📄 RIS: {os.path.basename(result['ris_file'])}")
        print(f"📊 Summary: {os.path.basename(result['summary_file'])}")
        print(f"📁 All files saved in: results/cite/")
        print(f"\n📈 Crossref API Results:")
        print(f"   ✓ Enhanced metadata: {result['crossref_hits']} papers")
        print(f"   ◐ CSV fallback: {result['crossref_misses']} papers")

        total_requests = result['crossref_hits'] + result['crossref_misses']
        if total_requests > 0:
            success_rate = result['crossref_hits'] / total_requests * 100
            print(f"   📊 Success rate: {success_rate:.1f}%")

        print(f"\n🔗 Citation format: ref1, ref2, ..., ref{result['total_papers']}")
        print("🎯 Ready for use in academic papers!")
