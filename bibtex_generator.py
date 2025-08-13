#!/usr/bin/env python3
"""
BibTeX Reference Generator
Generates BibTeX references from CSV data
"""

import pandas as pd
import re
import argparse
from datetime import datetime

class BibTeXGenerator:
    def __init__(self):
        pass
    
    def clean_text(self, text):
        """Clean text for BibTeX format"""
        if pd.isna(text) or text == '':
            return ''
        
        text = str(text)
        # Replace special characters
        text = text.replace('&', '\\&')
        text = text.replace('%', '\\%')
        text = text.replace('$', '\\$')
        text = text.replace('#', '\\#')
        text = text.replace('_', '\\_')
        text = text.replace('{', '\\{')
        text = text.replace('}', '\\}')
        
        return text
    
    def format_authors(self, authors_str):
        """Format authors for BibTeX"""
        if pd.isna(authors_str) or authors_str == '':
            return ''
        
        # Split authors by common delimiters
        authors = re.split(r'[;,]|and ', str(authors_str))
        authors = [author.strip() for author in authors if author.strip()]
        
        formatted_authors = []
        for author in authors[:3]:  # Limit to first 3 authors
            # Try to format as "Last, First"
            if ',' in author:
                formatted_authors.append(author)
            else:
                # Split by space and assume last word is surname
                parts = author.split()
                if len(parts) >= 2:
                    surname = parts[-1]
                    given_names = ' '.join(parts[:-1])
                    formatted_authors.append(f"{surname}, {given_names}")
                else:
                    formatted_authors.append(author)
        
        if len(authors) > 3:
            formatted_authors.append("others")
        
        return ' and '.join(formatted_authors)
    
    def generate_bibtex_entry(self, row):
        """Generate a single BibTeX entry"""
        paper_id = row.get('paper_id', '').replace('_', '')
        title = self.clean_text(row.get('title', ''))
        authors = self.format_authors(row.get('authors', ''))
        journal = self.clean_text(row.get('journal', ''))
        year = str(row.get('year', '')) if pd.notna(row.get('year')) else ''
        volume = str(row.get('volume', '')) if pd.notna(row.get('volume')) else ''
        issue = str(row.get('issue', '')) if pd.notna(row.get('issue')) else ''
        pages = self.clean_text(str(row.get('pages', ''))) if pd.notna(row.get('pages')) else ''
        publisher = self.clean_text(row.get('publisher', ''))
        doi = row.get('doi', '') if pd.notna(row.get('doi')) else ''
        paper_type = row.get('type', 'article')
        
        # Determine entry type
        entry_type = 'article'
        if 'proceedings' in journal.lower() or 'conference' in journal.lower():
            entry_type = 'inproceedings'
        elif 'workshop' in journal.lower():
            entry_type = 'inproceedings'
        elif paper_type == 'proceedings-article':
            entry_type = 'inproceedings'
        
        # Build BibTeX entry
        bibtex = f"@{entry_type}{{{paper_id},\n"
        
        if title:
            bibtex += f"  title={{{title}}},\n"
        
        if authors:
            bibtex += f"  author={{{authors}}},\n"
        
        if journal:
            if entry_type == 'inproceedings':
                bibtex += f"  booktitle={{{journal}}},\n"
            else:
                bibtex += f"  journal={{{journal}}},\n"
        
        if year:
            bibtex += f"  year={{{year}}},\n"
        
        if volume:
            bibtex += f"  volume={{{volume}}},\n"
        
        if issue:
            bibtex += f"  number={{{issue}}},\n"
        
        if pages:
            # Format pages
            pages = pages.replace('--', '--').replace('-', '--')
            bibtex += f"  pages={{{pages}}},\n"
        
        if publisher:
            bibtex += f"  publisher={{{publisher}}},\n"
        
        if doi:
            bibtex += f"  doi={{{doi}}},\n"
        
        # Remove trailing comma and close entry
        bibtex = bibtex.rstrip(',\n') + '\n'
        bibtex += "}\n"
        
        return bibtex
    
    def generate_bibtex_file(self, csv_path, output_path=None):
        """Generate BibTeX file from CSV"""
        df = pd.read_csv(csv_path)
        
        if output_path is None:
            base_name = csv_path.replace('.csv', '')
            output_path = f"{base_name}_references.bib"
        
        bibtex_entries = []
        
        print(f"Generating BibTeX references for {len(df)} papers...")
        
        for idx, row in df.iterrows():
            try:
                entry = self.generate_bibtex_entry(row)
                bibtex_entries.append(entry)
            except Exception as e:
                print(f"Error generating entry for row {idx}: {e}")
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("% BibTeX references generated from research paper CSV\n")
            f.write(f"% Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"% Total entries: {len(bibtex_entries)}\n\n")
            
            for entry in bibtex_entries:
                f.write(entry)
                f.write("\n")
        
        print(f"BibTeX file saved: {output_path}")
        print(f"Generated {len(bibtex_entries)} references")
        
        return output_path

def main():
    parser = argparse.ArgumentParser(description='Generate BibTeX references from CSV')
    parser.add_argument('--input', required=True, help='Input CSV file path')
    parser.add_argument('--output', help='Output BibTeX file path (optional)')
    
    args = parser.parse_args()
    
    generator = BibTeXGenerator()
    generator.generate_bibtex_file(args.input, args.output)

if __name__ == "__main__":
    main()
