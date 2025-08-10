#!/usr/bin/env python3
"""
Title Paper Finder
Takes titles from title_compare CSV files and checks for EXACT matches in Crossref API.
Only includes papers with exact title matches in the output.
"""

import pandas as pd
import requests
import time
import os
import re
from typing import Dict, Optional, List
from urllib.parse import quote


def search_crossref_exact_title(title: str) -> Optional[Dict]:
    """
    Search Crossref API for exact title match using quoted search.

    Args:
        title: The exact title to search for

    Returns:
        Dictionary with paper details if exact match found, None otherwise
    """
    try:
        # Clean the title and encode for URL
        clean_title = title.strip()
        # Use quoted search for exact match
        encoded_title = quote(f'"{clean_title}"')

        url = f"https://api.crossref.org/works?query.title={encoded_title}&rows=3"

        headers = {
            'User-Agent': 'ResearchHelper/1.0 (mailto:researcher@example.com)'
        }

        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        data = response.json()

        if data['message']['items']:
            # Check if any result is an exact title match
            for item in data['message']['items']:
                if 'title' in item and item['title']:
                    crossref_title = item['title'][0] if isinstance(item['title'], list) else item['title']

                    # Check for exact match (case-insensitive, normalized)
                    if normalize_title(clean_title) == normalize_title(crossref_title):
                        # Extract publication details
                        authors = []
                        if 'author' in item:
                            for author in item['author']:
                                if 'given' in author and 'family' in author:
                                    authors.append(f"{author['given']} {author['family']}")
                                elif 'family' in author:
                                    authors.append(author['family'])

                        return {
                            'original_title': clean_title,
                            'crossref_title': crossref_title,
                            'authors': '; '.join(authors) if authors else 'Not Available',
                            'journal': item.get('container-title', [''])[0] if item.get('container-title') else '',
                            'publisher': item.get('publisher', ''),
                            'year': str(item.get('published-print', {}).get('date-parts', [['']])[0][0] or
                                      item.get('published-online', {}).get('date-parts', [['']])[0][0] or ''),
                            'volume': item.get('volume', ''),
                            'issue': item.get('issue', ''),
                            'pages': item.get('page', ''),
                            'doi': item.get('DOI', ''),
                            'url': item.get('URL', ''),
                            'type': item.get('type', ''),
                            'score': item.get('score', 0)
                        }

        return None

    except Exception as e:
        print(f"    ❌ Error searching: {str(e)}")
        return None


def normalize_title(title: str) -> str:
    """Normalize title for comparison by removing punctuation and extra spaces."""
    # Convert to lowercase
    title = title.lower()
    # Remove punctuation and special characters
    title = re.sub(r'[^\w\s]', ' ', title)
    # Remove extra whitespace
    title = re.sub(r'\s+', ' ', title)
    return title.strip()


def process_title_compare_files(title_compare_dir: str) -> List[Dict]:
    """
    Process both titles_matched.csv and titles_different.csv files.

    Args:
        title_compare_dir: Path to the title_compare directory

    Returns:
        List of papers with exact Crossref matches
    """
    exact_matches = []

    # Files to process
    files_to_check = [
        'titles_matched.csv',
        'titles_different.csv'
    ]

    for filename in files_to_check:
        file_path = os.path.join(title_compare_dir, filename)

        if not os.path.exists(file_path):
            print(f"⚠️ File not found: {filename}")
            continue

        print(f"\n📖 Processing {filename}...")

        try:
            df = pd.read_csv(file_path)
            print(f"   Found {len(df)} papers to check")

            for idx, row in df.iterrows():
                paper_id = row.get('paper_id', '')
                csv_title = row.get('csv_title', '').strip()
                bibtex_title = row.get('bibtex_title', '').strip()

                print(f"\n[{idx+1:3d}/{len(df)}] {paper_id}")

                # Check CSV title first
                if csv_title:
                    print(f"   🔍 Checking CSV title: {csv_title[:60]}...")
                    csv_result = search_crossref_exact_title(csv_title)

                    if csv_result:
                        csv_result['paper_id'] = paper_id
                        csv_result['source_title'] = 'csv_title'
                        csv_result['source_file'] = filename
                        exact_matches.append(csv_result)
                        print(f"   ✅ EXACT MATCH found for CSV title!")

                        # Add delay and continue to next paper
                        time.sleep(0.3)
                        continue

                # Check BibTeX title if CSV didn't match
                if bibtex_title and bibtex_title != csv_title:
                    print(f"   🔍 Checking BibTeX title: {bibtex_title[:60]}...")
                    bibtex_result = search_crossref_exact_title(bibtex_title)

                    if bibtex_result:
                        bibtex_result['paper_id'] = paper_id
                        bibtex_result['source_title'] = 'bibtex_title'
                        bibtex_result['source_file'] = filename
                        exact_matches.append(bibtex_result)
                        print(f"   ✅ EXACT MATCH found for BibTeX title!")
                    else:
                        print(f"   ❌ No exact match found")
                else:
                    print(f"   ❌ No exact match found")

                # Rate limiting delay
                time.sleep(0.3)

        except Exception as e:
            print(f"❌ Error processing {filename}: {e}")

    return exact_matches


def save_exact_matches(exact_matches: List[Dict], output_dir: str) -> str:
    """
    Save the exact matches to a CSV file.

    Args:
        exact_matches: List of exact match dictionaries
        output_dir: Directory to save the output file

    Returns:
        Path to the saved file
    """
    if not exact_matches:
        print("⚠️ No exact matches found to save")
        return ""

    # Create DataFrame
    df = pd.DataFrame(exact_matches)

    # Reorder columns for better readability
    columns_order = [
        'paper_id', 'source_title', 'source_file', 'original_title', 'crossref_title',
        'authors', 'journal', 'year', 'volume', 'issue', 'pages',
        'publisher', 'doi', 'url', 'type', 'score'
    ]

    # Only include columns that exist
    available_columns = [col for col in columns_order if col in df.columns]
    df = df[available_columns]

    # Save to CSV
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"exact_crossref_matches_{timestamp}.csv")
    df.to_csv(output_file, index=False)

    return output_file


def main():
    """Main function to process titles and find exact Crossref matches."""
    print("🔍 Starting Exact Title Finder with Crossref API")
    print("📡 Searching for EXACT title matches only...")

    # Setup paths
    title_compare_dir = "/results/title_compare"
    output_dir = title_compare_dir  # Save results in the same directory

    # Check if title_compare directory exists
    if not os.path.exists(title_compare_dir):
        print(f"❌ Title compare directory not found: {title_compare_dir}")
        return

    print(f"📂 Processing files from: {title_compare_dir}")

    # Process the title comparison files
    exact_matches = process_title_compare_files(title_compare_dir)

    # Print summary
    print(f"\n📊 SEARCH SUMMARY")
    print("=" * 50)
    print(f"🎯 Exact matches found: {len(exact_matches)}")

    if exact_matches:
        # Count by source file
        from collections import Counter
        file_counts = Counter(match['source_file'] for match in exact_matches)
        source_counts = Counter(match['source_title'] for match in exact_matches)

        print(f"\n📄 Matches by source file:")
        for filename, count in file_counts.items():
            print(f"   {filename}: {count} matches")

        print(f"\n📝 Matches by title source:")
        for source, count in source_counts.items():
            print(f"   {source}: {count} matches")

        # Save results
        output_file = save_exact_matches(exact_matches, output_dir)
        print(f"\n💾 Results saved to: {output_file}")

        # Show sample matches
        print(f"\n📋 SAMPLE EXACT MATCHES:")
        print("-" * 50)
        for i, match in enumerate(exact_matches[:5]):
            print(f"{i+1}. {match['paper_id']} ({match['source_title']})")
            print(f"   Title: {match['original_title'][:60]}...")
            print(f"   Authors: {match['authors'][:50]}...")
            print(f"   Journal: {match['journal']}")
            print(f"   Year: {match['year']}")
            print()
    else:
        print("❌ No exact matches found in Crossref database")

    print("🎯 Analysis complete!")


if __name__ == "__main__":
    main()
