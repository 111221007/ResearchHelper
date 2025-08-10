#!/usr/bin/env python3
"""
Generate citations from consolidated_papers.csv using CSV data as primary source.
This approach creates properly formatted citations from your existing data.
"""

import pandas as pd
import time
import os
from typing import List, Dict

class CSVCitationGenerator:
    """
    Generate citations directly from CSV data for reliable and fast processing.
    """

    def __init__(self):
        self.citations = []

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

    def format_bibtex_entry(self, paper: Dict, cite_key: str) -> str:
        """Format paper as BibTeX entry in standard academic format."""
        bibtex_lines = []
        bibtex_lines.append(f"@article{{{cite_key},")

        if paper.get('title'):
            # Clean title for BibTeX
            title = paper['title'].replace('{', '').replace('}', '')
            bibtex_lines.append(f"  title={{{title}}},")

        # Use Anonymous as default author
        bibtex_lines.append(f"  author={{Anonymous}},")

        if paper.get('venue'):
            venue = paper['venue'].replace('{', '').replace('}', '')
            bibtex_lines.append(f"  journal={{{venue}}},")

        # Add volume, number, and pages as empty placeholders for standard format
        bibtex_lines.append(f"  volume={{}},")
        bibtex_lines.append(f"  number={{}},")
        bibtex_lines.append(f"  pages={{}},")

        if paper.get('year'):
            bibtex_lines.append(f"  year={{{paper['year']}}},")

        # Add publisher as placeholder
        bibtex_lines.append(f"  publisher={{}}")

        bibtex_lines.append("}")
        bibtex_lines.append("")  # Empty line

        return "\n".join(bibtex_lines)

    def format_ris_entry(self, paper: Dict) -> str:
        """Format paper as RIS entry."""
        ris_lines = []
        ris_lines.append("TY  - JOUR")  # Type: Journal Article

        if paper.get('title'):
            ris_lines.append(f"TI  - {paper['title']}")

        ris_lines.append("AU  - Anonymous")

        if paper.get('venue'):
            ris_lines.append(f"JO  - {paper['venue']}")

        if paper.get('year'):
            ris_lines.append(f"PY  - {paper['year']}")

        if paper.get('keywords'):
            ris_lines.append(f"KW  - {paper['keywords']}")

        if paper.get('category'):
            ris_lines.append(f"AB  - Category: {paper['category']}")

        ris_lines.append("ER  - ")  # End of record
        ris_lines.append("")  # Empty line

        return "\n".join(ris_lines)

    def generate_all_citations(self, csv_file_path: str, output_format: str = 'both'):
        """Generate citations for all papers in CSV."""
        papers = self.read_papers_from_csv(csv_file_path)

        if not papers:
            print("No papers found to process.")
            return

        # Create cite directory if it doesn't exist
        cite_dir = os.path.join(os.path.dirname(csv_file_path), 'cite')
        os.makedirs(cite_dir, exist_ok=True)

        timestamp = time.strftime("%Y%m%d_%H%M%S")

        # Generate BibTeX
        if output_format in ['bibtex', 'both']:
            bibtex_filename = os.path.join(cite_dir, f"all_papers_citations_{timestamp}.bib")
            with open(bibtex_filename, 'w', encoding='utf-8') as f:
                f.write("% BibTeX citations for all papers in consolidated dataset\n")
                f.write(f"% Generated on {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"% Total papers: {len(papers)}\n\n")

                for i, paper in enumerate(papers, 1):
                    cite_key = f"ref{i}"
                    f.write(self.format_bibtex_entry(paper, cite_key))

            print(f"BibTeX citations saved to: {bibtex_filename}")

        # Generate RIS
        if output_format in ['ris', 'both']:
            ris_filename = os.path.join(cite_dir, f"all_papers_citations_{timestamp}.ris")
            with open(ris_filename, 'w', encoding='utf-8') as f:
                for paper in papers:
                    f.write(self.format_ris_entry(paper))

            print(f"RIS citations saved to: {ris_filename}")

        # Generate metrics-based citation files
        self.generate_metric_citations(papers, timestamp, cite_dir)

        print(f"\n=== Summary ===")
        print(f"Total papers processed: {len(papers)}")
        print(f"Citations generated: {len(papers)}")
        print(f"Success rate: 100.0%")
        print(f"All citation files saved in: {cite_dir}")

    def generate_metric_citations(self, papers: List[Dict], timestamp: str, cite_dir: str):
        """Generate separate citation files for each metric category."""
        # Define metric categories
        metrics = ["Latency", "Reliability & QoS", "Security & Privacy", "Cost",
                  "Energy Consumption", "Resource Management", "Benchmarking & Evaluation"]

        for metric in metrics:
            # Filter papers by checking titles, categories, and keywords
            metric_papers = []
            metric_keywords = self.get_metric_keywords(metric)

            for paper in papers:
                title = str(paper.get('title', '')).lower()
                category = str(paper.get('category', '')).lower()
                keywords = str(paper.get('keywords', '')).lower()
                combined_text = f"{title} {category} {keywords}"

                if any(keyword.lower() in combined_text for keyword in metric_keywords):
                    metric_papers.append(paper)

            if metric_papers:
                # Generate BibTeX for this metric
                safe_metric = metric.lower().replace(" & ", "_").replace(" ", "_")
                bibtex_filename = os.path.join(cite_dir, f"{safe_metric}_citations_{timestamp}.bib")

                with open(bibtex_filename, 'w', encoding='utf-8') as f:
                    f.write(f"% {metric} Papers Citations\n")
                    f.write(f"% Total papers: {len(metric_papers)}\n\n")

                    for i, paper in enumerate(metric_papers, 1):
                        cite_key = f"{safe_metric}{i:03d}"
                        f.write(self.format_bibtex_entry(paper, cite_key))

                print(f"{metric} citations ({len(metric_papers)} papers) saved to: {bibtex_filename}")

    def get_metric_keywords(self, metric: str) -> List[str]:
        """Get keywords for each metric category."""
        keyword_map = {
            "Latency": ["latency", "cold start", "response time", "delay", "startup"],
            "Reliability & QoS": ["reliability", "qos", "quality of service", "fairness", "sla"],
            "Security & Privacy": ["security", "privacy", "authentication", "vulnerability"],
            "Cost": ["cost", "pricing", "economic", "billing", "financial"],
            "Energy Consumption": ["energy", "power", "consumption", "carbon", "green"],
            "Resource Management": ["resource", "scheduling", "allocation", "provisioning", "autoscaling"],
            "Benchmarking & Evaluation": ["benchmark", "evaluation", "performance", "test", "comparison"]
        }
        return keyword_map.get(metric, [])

def main():
    """Main function to generate citations from consolidated_papers.csv"""

    # Set up file paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(current_dir)
    csv_file = os.path.join(project_dir, 'results', 'consolidated_papers.csv')

    # Check if CSV file exists
    if not os.path.exists(csv_file):
        print(f"Error: Could not find consolidated_papers.csv at {csv_file}")
        return

    # Initialize citation generator
    generator = CSVCitationGenerator()

    # Generate all citations
    generator.generate_all_citations(
        csv_file_path=csv_file,
        output_format='both'  # Generate both RIS and BibTeX formats
    )

if __name__ == "__main__":
    main()
