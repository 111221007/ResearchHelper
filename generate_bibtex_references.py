#!/usr/bin/env python3
"""
Script to generate BibTeX references from serverless papers CSV data.
"""

import pandas as pd
import re
from datetime import datetime

def clean_title(title):
    """Clean title for BibTeX format."""
    if pd.isna(title):
        return "Unknown Title"
    # Remove special characters that might break BibTeX
    title = str(title).strip()
    # Handle HTML entities
    title = title.replace('&', '\\&')
    title = title.replace('<i>', '').replace('</i>', '')
    title = title.replace('<b>', '').replace('</b>', '')
    return title

def clean_authors(authors):
    """Clean and format authors for BibTeX."""
    if pd.isna(authors):
        return "Unknown Author"
    
    # Split authors by semicolon and clean each
    author_list = str(authors).split(';')
    cleaned_authors = []
    
    for author in author_list:
        author = author.strip()
        if author:
            # Handle "Last, First" or "First Last" formats
            if ',' in author:
                # Already in "Last, First" format
                cleaned_authors.append(author.strip())
            else:
                # Convert "First Last" to "Last, First"
                parts = author.strip().split()
                if len(parts) >= 2:
                    last_name = parts[-1]
                    first_names = ' '.join(parts[:-1])
                    cleaned_authors.append(f"{last_name}, {first_names}")
                else:
                    cleaned_authors.append(author)
    
    return ' and '.join(cleaned_authors)

def clean_journal(journal):
    """Clean journal name for BibTeX."""
    if pd.isna(journal):
        return "Unknown Journal"
    return str(journal).strip()

def clean_publisher(publisher):
    """Clean publisher name for BibTeX."""
    if pd.isna(publisher):
        return "Unknown Publisher"
    return str(publisher).strip()

def clean_pages(pages):
    """Clean and format page numbers for BibTeX."""
    if pd.isna(pages):
        return ""
    pages_str = str(pages).strip()
    if pages_str:
        # Replace dashes with double dashes for BibTeX
        pages_str = pages_str.replace('-', '--')
        return pages_str
    return ""

def clean_volume_issue(value):
    """Clean volume or issue numbers."""
    if pd.isna(value):
        return ""
    return str(value).strip()

def determine_entry_type(paper_type, journal):
    """Determine BibTeX entry type based on paper type and journal."""
    if pd.isna(paper_type):
        paper_type = ""
    
    paper_type = str(paper_type).lower()
    journal = str(journal).lower() if not pd.isna(journal) else ""
    
    # Check for conference proceedings
    if 'proceedings' in paper_type or 'conference' in paper_type:
        return 'inproceedings'
    elif 'proceedings' in journal or 'conference' in journal or 'workshop' in journal:
        return 'inproceedings'
    # Check for journal articles
    elif 'journal' in paper_type or 'article' in paper_type:
        return 'article'
    elif 'journal' in journal:
        return 'article'
    # Default to article
    else:
        return 'article'

def generate_bibtex_entry(row):
    """Generate a single BibTeX entry from a CSV row."""
    paper_id = str(row['paper_id']).strip()
    entry_type = determine_entry_type(row.get('type', ''), row.get('journal', ''))
    
    # Clean all fields
    title = clean_title(row['title'])
    authors = clean_authors(row['authors'])
    journal = clean_journal(row['journal'])
    year = str(row['year']).strip() if not pd.isna(row['year']) else ""
    volume = clean_volume_issue(row.get('volume', ''))
    issue = clean_volume_issue(row.get('issue', ''))
    pages = clean_pages(row.get('pages', ''))
    publisher = clean_publisher(row.get('publisher', ''))
    doi = str(row['doi']).strip() if not pd.isna(row['doi']) else ""
    
    # Start building the BibTeX entry
    bibtex = f"@{entry_type}{{{paper_id},\n"
    bibtex += f"  title={{{title}}},\n"
    bibtex += f"  author={{{authors}}},\n"
    
    # Add journal/booktitle based on entry type
    if entry_type == 'article':
        bibtex += f"  journal={{{journal}}},\n"
    else:  # inproceedings
        bibtex += f"  booktitle={{{journal}}},\n"
    
    # Add year
    if year:
        bibtex += f"  year={{{year}}},\n"
    
    # Add volume if available
    if volume:
        bibtex += f"  volume={{{volume}}},\n"
    
    # Add issue/number if available
    if issue:
        if entry_type == 'article':
            bibtex += f"  number={{{issue}}},\n"
        else:
            bibtex += f"  number={{{issue}}},\n"
    
    # Add pages if available
    if pages:
        bibtex += f"  pages={{{pages}}},\n"
    
    # Add publisher if available
    if publisher:
        bibtex += f"  publisher={{{publisher}}},\n"
    
    # Add DOI if available
    if doi:
        bibtex += f"  doi={{{doi}}},\n"
    
    # Remove trailing comma and close the entry
    bibtex = bibtex.rstrip(',\n') + '\n}\n'
    
    return bibtex

def main():
    # Read the CSV file
    input_path = "/Users/reddy/2025/ResearchHelper/results/final/serverless_survey_papers.csv"
    
    try:
        df = pd.read_csv(input_path)
        print(f"Loaded {len(df)} papers from CSV")
    except FileNotFoundError:
        print(f"Error: File not found: {input_path}")
        return
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return
    
    # Generate BibTeX entries
    bibtex_entries = []
    total_papers = len(df)
    
    print(f"Generating BibTeX entries for {total_papers} papers...")
    
    for idx, row in df.iterrows():
        try:
            entry = generate_bibtex_entry(row)
            bibtex_entries.append(entry)
            
            if (idx + 1) % 50 == 0:
                print(f"Processed {idx + 1}/{total_papers} papers...")
                
        except Exception as e:
            print(f"Error processing paper {row.get('paper_id', 'unknown')}: {e}")
            continue
    
    # Create output content
    header = f"""% BibTeX References for Serverless Computing Survey Papers
% Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
% Total entries: {len(bibtex_entries)}

"""
    
    output_content = header + '\n'.join(bibtex_entries)
    
    # Save to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"/Users/reddy/2025/ResearchHelper/results/final/serverless_papers_references_{timestamp}.bib"
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(output_content)
        
        print(f"\nBibTeX references saved to: {output_path}")
        print(f"Successfully generated {len(bibtex_entries)} BibTeX entries")
        
        # Show sample entries
        print(f"\nSample BibTeX entries:")
        print("=" * 50)
        for i, entry in enumerate(bibtex_entries[:2]):
            print(f"Entry {i+1}:")
            print(entry)
            if i < 1:
                print("-" * 30)
        
        # Statistics
        entry_types = {}
        for entry in bibtex_entries:
            entry_type = entry.split('{')[0].replace('@', '')
            entry_types[entry_type] = entry_types.get(entry_type, 0) + 1
        
        print(f"\nEntry type distribution:")
        for entry_type, count in sorted(entry_types.items()):
            print(f"  {entry_type}: {count} entries")
            
    except Exception as e:
        print(f"Error saving file: {e}")

if __name__ == "__main__":
    main()
