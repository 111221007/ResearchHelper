#!/usr/bin/env python3
"""
Title Comparison Tool
Compares titles from consolidated_papers.csv with crossref_citations_20250810_065645.bib
and generates a detailed comparison report.
"""

import pandas as pd
import re
import os
from typing import List, Dict, Tuple
from difflib import SequenceMatcher


def extract_titles_from_csv(csv_file_path: str) -> List[Dict]:
    """Extract titles from consolidated_papers.csv"""
    try:
        df = pd.read_csv(csv_file_path)
        titles = []
        for idx, row in df.iterrows():
            titles.append({
                'id': idx + 1,
                'title': row.get('title', '').strip(),
                'source': 'CSV'
            })
        return titles
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return []


def extract_titles_from_bibtex(bib_file_path: str) -> List[Dict]:
    """Extract titles from BibTeX file"""
    try:
        titles = []
        with open(bib_file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract title entries using regex
        title_pattern = r'@\w+\{ref(\d+),.*?title=\{([^}]+)\}'
        matches = re.findall(title_pattern, content, re.DOTALL)

        for ref_num, title in matches:
            titles.append({
                'id': int(ref_num),
                'title': title.strip(),
                'source': 'BibTeX'
            })

        return titles
    except Exception as e:
        print(f"Error reading BibTeX file: {e}")
        return []


def clean_title_for_comparison(title: str) -> str:
    """Clean and normalize title for comparison"""
    # Convert to lowercase
    title = title.lower()
    # Remove extra whitespace
    title = re.sub(r'\s+', ' ', title)
    # Remove special characters and punctuation
    title = re.sub(r'[^\w\s]', '', title)
    # Strip whitespace
    return title.strip()


def calculate_similarity(title1: str, title2: str) -> float:
    """Calculate similarity between two titles using SequenceMatcher"""
    clean1 = clean_title_for_comparison(title1)
    clean2 = clean_title_for_comparison(title2)
    return SequenceMatcher(None, clean1, clean2).ratio()


def compare_titles(csv_titles: List[Dict], bibtex_titles: List[Dict]) -> List[Dict]:
    """Compare titles and generate comparison results"""
    comparison_results = []

    # Create dictionaries for easy lookup
    csv_dict = {item['id']: item for item in csv_titles}
    bibtex_dict = {item['id']: item for item in bibtex_titles}

    # Get all IDs
    all_ids = set(csv_dict.keys()) | set(bibtex_dict.keys())

    for paper_id in sorted(all_ids):
        csv_title = csv_dict.get(paper_id, {}).get('title', '')
        bibtex_title = bibtex_dict.get(paper_id, {}).get('title', '')

        # Calculate similarity
        if csv_title and bibtex_title:
            similarity = calculate_similarity(csv_title, bibtex_title)

            # Determine match status
            if similarity >= 0.9:
                match_status = "EXACT_MATCH"
            elif similarity >= 0.7:
                match_status = "SIMILAR_MATCH"
            elif similarity >= 0.5:
                match_status = "PARTIAL_MATCH"
            else:
                match_status = "DIFFERENT"
        else:
            similarity = 0.0
            match_status = "MISSING"

        comparison_results.append({
            'paper_id': f"ref{paper_id}",
            'csv_title': csv_title,
            'bibtex_title': bibtex_title,
            'similarity_score': round(similarity, 3),
            'match_status': match_status,
            'csv_present': bool(csv_title),
            'bibtex_present': bool(bibtex_title),
            'title_length_csv': len(csv_title) if csv_title else 0,
            'title_length_bibtex': len(bibtex_title) if bibtex_title else 0
        })

    return comparison_results


def generate_summary_stats(comparison_results: List[Dict]) -> Dict:
    """Generate summary statistics"""
    total_papers = len(comparison_results)

    # Count by match status
    status_counts = {}
    for result in comparison_results:
        status = result['match_status']
        status_counts[status] = status_counts.get(status, 0) + 1

    # Calculate percentages
    stats = {
        'total_papers': total_papers,
        'exact_matches': status_counts.get('EXACT_MATCH', 0),
        'similar_matches': status_counts.get('SIMILAR_MATCH', 0),
        'partial_matches': status_counts.get('PARTIAL_MATCH', 0),
        'different_titles': status_counts.get('DIFFERENT', 0),
        'missing_entries': status_counts.get('MISSING', 0)
    }

    # Add percentages
    for key in ['exact_matches', 'similar_matches', 'partial_matches', 'different_titles', 'missing_entries']:
        stats[f'{key}_percent'] = round(stats[key] / total_papers * 100, 1) if total_papers > 0 else 0

    return stats


def main():
    """Main function to compare titles and generate report"""
    print("🔍 Starting title comparison analysis...")

    # File paths
    csv_file = "/results/consolidated_papers.csv"
    bibtex_file = "/results/cite/crossref_citations_20250810_065645.bib"
    output_dir = "/results/title_compare"

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Check if files exist
    if not os.path.exists(csv_file):
        print(f"❌ CSV file not found: {csv_file}")
        return

    if not os.path.exists(bibtex_file):
        print(f"❌ BibTeX file not found: {bibtex_file}")
        return

    # Extract titles
    print("📖 Extracting titles from CSV file...")
    csv_titles = extract_titles_from_csv(csv_file)
    print(f"   Found {len(csv_titles)} titles in CSV")

    print("📖 Extracting titles from BibTeX file...")
    bibtex_titles = extract_titles_from_bibtex(bibtex_file)
    print(f"   Found {len(bibtex_titles)} titles in BibTeX")

    # Compare titles
    print("🔄 Comparing titles...")
    comparison_results = compare_titles(csv_titles, bibtex_titles)

    # Generate summary statistics
    stats = generate_summary_stats(comparison_results)

    # Create output DataFrame
    df_comparison = pd.DataFrame(comparison_results)

    # Save detailed comparison to CSV
    comparison_file = os.path.join(output_dir, "title_comparison_detailed.csv")
    df_comparison.to_csv(comparison_file, index=False)
    print(f"📄 Detailed comparison saved to: {comparison_file}")

    # Separate matched and different titles
    print("📋 Separating matched and different titles...")

    # MATCHED TITLES: Exact matches and similar matches (≥70% similarity)
    matched_titles = df_comparison[
        (df_comparison['match_status'] == 'EXACT_MATCH') |
        (df_comparison['match_status'] == 'SIMILAR_MATCH')
    ].copy()

    # Add additional info for matched titles
    matched_titles['match_type'] = matched_titles['match_status']
    matched_titles['notes'] = matched_titles.apply(
        lambda row: 'Perfect match' if row['match_status'] == 'EXACT_MATCH'
        else f'Similar match ({row["similarity_score"]*100:.1f}% similarity)', axis=1
    )

    # DIFFERENT TITLES: Partial matches, different, and missing entries
    different_titles = df_comparison[
        (df_comparison['match_status'] == 'PARTIAL_MATCH') |
        (df_comparison['match_status'] == 'DIFFERENT') |
        (df_comparison['match_status'] == 'MISSING')
    ].copy()

    # Add additional info for different titles
    different_titles['difference_type'] = different_titles['match_status']
    different_titles['notes'] = different_titles.apply(
        lambda row: f'Partial similarity ({row["similarity_score"]*100:.1f}%)' if row['match_status'] == 'PARTIAL_MATCH'
        else f'Very different ({row["similarity_score"]*100:.1f}%)' if row['match_status'] == 'DIFFERENT'
        else 'Missing entry', axis=1
    )

    # Save matched titles CSV
    matched_file = os.path.join(output_dir, "titles_matched.csv")
    matched_columns = [
        'paper_id', 'csv_title', 'bibtex_title', 'similarity_score',
        'match_type', 'notes', 'title_length_csv', 'title_length_bibtex'
    ]
    matched_titles[matched_columns].to_csv(matched_file, index=False)
    print(f"✅ Matched titles saved to: {matched_file}")
    print(f"   Found {len(matched_titles)} matched papers")

    # Save different titles CSV
    different_file = os.path.join(output_dir, "titles_different.csv")
    different_columns = [
        'paper_id', 'csv_title', 'bibtex_title', 'similarity_score',
        'difference_type', 'notes', 'title_length_csv', 'title_length_bibtex'
    ]
    different_titles[different_columns].to_csv(different_file, index=False)
    print(f"🔴 Different titles saved to: {different_file}")
    print(f"   Found {len(different_titles)} different papers")

    # Create summary DataFrame
    summary_data = [
        ["Total Papers", stats['total_papers'], "100.0%"],
        ["Exact Matches (≥90% similarity)", stats['exact_matches'], f"{stats['exact_matches_percent']}%"],
        ["Similar Matches (70-89% similarity)", stats['similar_matches'], f"{stats['similar_matches_percent']}%"],
        ["Partial Matches (50-69% similarity)", stats['partial_matches'], f"{stats['partial_matches_percent']}%"],
        ["Different Titles (<50% similarity)", stats['different_titles'], f"{stats['different_titles_percent']}%"],
        ["Missing Entries", stats['missing_entries'], f"{stats['missing_entries_percent']}%"],
        ["", "", ""],
        ["MATCHED PAPERS (Exact + Similar)", stats['exact_matches'] + stats['similar_matches'],
         f"{stats['exact_matches_percent'] + stats['similar_matches_percent']}%"],
        ["DIFFERENT PAPERS (Partial + Different + Missing)",
         stats['partial_matches'] + stats['different_titles'] + stats['missing_entries'],
         f"{stats['partial_matches_percent'] + stats['different_titles_percent'] + stats['missing_entries_percent']}%"]
    ]

    df_summary = pd.DataFrame(summary_data, columns=['Category', 'Count', 'Percentage'])

    # Save summary to CSV
    summary_file = os.path.join(output_dir, "title_comparison_summary.csv")
    df_summary.to_csv(summary_file, index=False)
    print(f"📊 Summary saved to: {summary_file}")

    # Print summary to console
    print("\n📊 TITLE COMPARISON SUMMARY")
    print("=" * 50)
    print(f"Total Papers Analyzed: {stats['total_papers']}")
    print(f"✅ Exact Matches: {stats['exact_matches']} ({stats['exact_matches_percent']}%)")
    print(f"🟡 Similar Matches: {stats['similar_matches']} ({stats['similar_matches_percent']}%)")
    print(f"🟠 Partial Matches: {stats['partial_matches']} ({stats['partial_matches_percent']}%)")
    print(f"🔴 Different Titles: {stats['different_titles']} ({stats['different_titles_percent']}%)")
    print(f"⚪ Missing Entries: {stats['missing_entries']} ({stats['missing_entries_percent']}%)")

    print("\n📋 FILE SEPARATION RESULTS")
    print("=" * 50)
    print(f"✅ MATCHED PAPERS: {len(matched_titles)} papers")
    print(f"   📄 File: titles_matched.csv")
    print(f"   📝 Includes: Exact matches + Similar matches (≥70% similarity)")

    print(f"\n🔴 DIFFERENT PAPERS: {len(different_titles)} papers")
    print(f"   📄 File: titles_different.csv")
    print(f"   📝 Includes: Partial matches + Different titles + Missing entries")

    # Show some examples from each category
    print("\n📋 SAMPLE FROM MATCHED TITLES")
    print("=" * 50)
    if not matched_titles.empty:
        sample_matched = matched_titles.head(3)
        for _, row in sample_matched.iterrows():
            print(f"  ✅ {row['paper_id']}: {row['csv_title'][:50]}...")
            if row['match_type'] == 'SIMILAR_MATCH':
                print(f"     → {row['bibtex_title'][:50]}... ({row['similarity_score']:.3f})")

    print("\n📋 SAMPLE FROM DIFFERENT TITLES")
    print("=" * 50)
    if not different_titles.empty:
        sample_different = different_titles.head(3)
        for _, row in sample_different.iterrows():
            print(f"  🔴 {row['paper_id']} ({row['difference_type']}):")
            print(f"     CSV: {row['csv_title'][:50]}...")
            print(f"     BibTeX: {row['bibtex_title'][:50]}...")
            print(f"     Similarity: {row['similarity_score']:.3f}")

    print(f"\n🎯 Analysis complete! Files generated:")
    print(f"   📄 All comparisons: {comparison_file}")
    print(f"   ✅ Matched titles: {matched_file}")
    print(f"   🔴 Different titles: {different_file}")
    print(f"   📊 Summary: {summary_file}")


if __name__ == "__main__":
    main()
