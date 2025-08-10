import csv
import time
import re
from scholarly import scholarly
from typing import List, Dict, Optional
import pandas as pd


class CitationProcessor:
    """
    Processes academic titles from CSV and generates RIS citations using scholarly library.
    """

    def __init__(self, delay: float = 2.0):
        """
        Initialize the citation processor.

        Args:
            delay: Delay between requests to avoid rate limiting (seconds)
        """
        self.delay = delay
        self.citations = []

    def read_papers_from_csv(self, csv_file_path: str) -> List[Dict]:
        """
        Read complete paper information from CSV file.

        Args:
            csv_file_path: Path to the CSV file

        Returns:
            List of paper dictionaries
        """
        papers = []
        try:
            df = pd.read_csv(csv_file_path)
            for _, row in df.iterrows():
                paper = {
                    'id': row.get('consolidated_id', ''),
                    'title': row.get('title', ''),
                    'year': row.get('year', ''),
                    'venue': row.get('venue', ''),
                    'category': row.get('category', ''),
                    'keywords': row.get('keywords', ''),
                    'authors': 'Anonymous',  # Default since most papers don't have author info
                }
                papers.append(paper)
        except Exception as e:
            print(f"Error reading CSV file: {e}")

        return papers

    def create_citation_from_csv_data(self, paper: Dict) -> Dict:
        """
        Create citation information from CSV data when scholarly search fails.

        Args:
            paper: Paper dictionary from CSV

        Returns:
            Citation dictionary
        """
        citation = {
            'title': paper.get('title', ''),
            'authors': [paper.get('authors', 'Anonymous')],
            'journal': paper.get('venue', ''),
            'year': str(paper.get('year', '')),
            'volume': '',
            'number': '',
            'pages': '',
            'doi': '',
            'abstract': f"Keywords: {paper.get('keywords', '')}. Category: {paper.get('category', '')}",
            'url': '',
            'source': 'csv_data'
        }
        return citation

    def read_titles_from_csv(self, csv_file_path: str, title_column: str = 'title') -> List[str]:
        """
        Read titles from a CSV file.

        Args:
            csv_file_path: Path to the CSV file
            title_column: Name of the column containing titles

        Returns:
            List of titles
        """
        titles = []
        try:
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if title_column in row and row[title_column].strip():
                        titles.append(row[title_column].strip())
        except FileNotFoundError:
            print(f"Error: CSV file '{csv_file_path}' not found.")
        except KeyError:
            print(f"Error: Column '{title_column}' not found in CSV file.")

        return titles

    def search_citation(self, title: str) -> Optional[Dict]:
        """
        Search for a citation using the scholarly library with fallback strategies.

        Args:
            title: Academic paper title to search for

        Returns:
            Dictionary containing citation information or None if not found
        """
        try:
            # Try exact title search first
            search_query = scholarly.search_pubs(title)
            publication = next(search_query, None)

            if publication:
                pub_filled = scholarly.fill(publication)
                return self.extract_citation_info(pub_filled)

            # Try with shortened title if exact search fails
            if len(title) > 50:
                short_title = title[:50]
                search_query = scholarly.search_pubs(short_title)
                publication = next(search_query, None)

                if publication:
                    pub_filled = scholarly.fill(publication)
                    return self.extract_citation_info(pub_filled)

            # Try searching for key terms
            key_terms = self.extract_key_terms(title)
            if key_terms:
                search_query = scholarly.search_pubs(key_terms)
                publication = next(search_query, None)

                if publication:
                    pub_filled = scholarly.fill(publication)
                    return self.extract_citation_info(pub_filled)

            return None

        except Exception as e:
            print(f"Error searching for '{title[:50]}...': {str(e)}")
            return None

    def extract_key_terms(self, title: str) -> str:
        """
        Extract key terms from title for alternative search.

        Args:
            title: Paper title

        Returns:
            String with key terms
        """
        # Remove common words and keep important terms
        common_words = {'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'using', 'based'}
        words = title.lower().split()
        key_words = [word for word in words if word not in common_words and len(word) > 3]
        return ' '.join(key_words[:5])  # Use first 5 key terms

    def extract_citation_info(self, publication) -> Dict:
        """
        Extract relevant citation information from scholarly publication object.

        Args:
            publication: Filled publication object from scholarly

        Returns:
            Dictionary with citation information
        """
        citation = {
            'title': publication.get('bib', {}).get('title', ''),
            'authors': publication.get('bib', {}).get('author', []),
            'journal': publication.get('bib', {}).get('venue', ''),
            'year': publication.get('bib', {}).get('pub_year', ''),
            'volume': publication.get('bib', {}).get('volume', ''),
            'number': publication.get('bib', {}).get('number', ''),
            'pages': publication.get('bib', {}).get('pages', ''),
            'doi': publication.get('pub_url', ''),
            'abstract': publication.get('bib', {}).get('abstract', ''),
            'url': publication.get('pub_url', '')
        }

        return citation

    def format_ris_entry(self, citation: Dict) -> str:
        """
        Format citation information as RIS (Research Information Systems) entry.

        Args:
            citation: Dictionary containing citation information

        Returns:
            Formatted RIS entry as string
        """
        ris_entry = []
        ris_entry.append("TY  - JOUR")  # Type: Journal Article

        if citation.get('title'):
            ris_entry.append(f"TI  - {citation['title']}")

        # Handle multiple authors
        authors = citation.get('authors', [])
        if isinstance(authors, list):
            for author in authors:
                ris_entry.append(f"AU  - {author}")
        elif isinstance(authors, str):
            ris_entry.append(f"AU  - {authors}")

        if citation.get('journal'):
            ris_entry.append(f"JO  - {citation['journal']}")

        if citation.get('year'):
            ris_entry.append(f"PY  - {citation['year']}")

        if citation.get('volume'):
            ris_entry.append(f"VL  - {citation['volume']}")

        if citation.get('number'):
            ris_entry.append(f"IS  - {citation['number']}")

        if citation.get('pages'):
            ris_entry.append(f"SP  - {citation['pages']}")

        if citation.get('doi'):
            ris_entry.append(f"DO  - {citation['doi']}")

        if citation.get('url'):
            ris_entry.append(f"UR  - {citation['url']}")

        if citation.get('abstract'):
            ris_entry.append(f"AB  - {citation['abstract']}")

        ris_entry.append("ER  - ")  # End of record
        ris_entry.append("")  # Empty line between entries

        return "\n".join(ris_entry)

    def format_bibtex_entry(self, citation: Dict, cite_key: str = None) -> str:
        """
        Format citation information as BibTeX entry.

        Args:
            citation: Dictionary containing citation information
            cite_key: Citation key for BibTeX (generated if not provided)

        Returns:
            Formatted BibTeX entry as string
        """
        if not cite_key:
            # Generate cite key from first author last name and year
            authors = citation.get('authors', [])
            if isinstance(authors, list) and authors:
                first_author = authors[0].split()[-1] if authors[0] else "Unknown"
            elif isinstance(authors, str):
                first_author = authors.split()[-1] if authors else "Unknown"
            else:
                first_author = "Unknown"

            year = citation.get('year', 'NoYear')
            cite_key = f"{first_author}{year}".replace(' ', '')

        bibtex_entry = []
        bibtex_entry.append(f"@article{{{cite_key},")

        if citation.get('title'):
            bibtex_entry.append(f"  title={{{citation['title']}}},")

        # Format authors
        authors = citation.get('authors', [])
        if isinstance(authors, list) and authors:
            author_str = " and ".join(authors)
            bibtex_entry.append(f"  author={{{author_str}}},")
        elif isinstance(authors, str) and authors:
            bibtex_entry.append(f"  author={{{authors}}},")

        if citation.get('journal'):
            bibtex_entry.append(f"  journal={{{citation['journal']}}},")

        if citation.get('year'):
            bibtex_entry.append(f"  year={{{citation['year']}}},")

        if citation.get('volume'):
            bibtex_entry.append(f"  volume={{{citation['volume']}}},")

        if citation.get('number'):
            bibtex_entry.append(f"  number={{{citation['number']}}},")

        if citation.get('pages'):
            bibtex_entry.append(f"  pages={{{citation['pages']}}},")

        if citation.get('doi'):
            bibtex_entry.append(f"  doi={{{citation['doi']}}},")

        if citation.get('url'):
            bibtex_entry.append(f"  url={{{citation['url']}}},")

        # Remove trailing comma from last entry
        if bibtex_entry[-1].endswith(','):
            bibtex_entry[-1] = bibtex_entry[-1][:-1]

        bibtex_entry.append("}")
        bibtex_entry.append("")  # Empty line between entries

        return "\n".join(bibtex_entry)

    def process_csv_citations(self, csv_file_path: str, max_papers: int = None,
                            output_format: str = 'both') -> None:
        """
        Process all titles from CSV and generate citations.

        Args:
            csv_file_path: Path to the consolidated papers CSV file
            max_papers: Maximum number of papers to process (None for all)
            output_format: 'ris', 'bibtex', or 'both'
        """
        print(f"Reading titles from: {csv_file_path}")
        titles = self.read_titles_from_csv(csv_file_path, 'title')

        if not titles:
            print("No titles found in the CSV file.")
            return

        # Limit number of papers if specified
        if max_papers:
            titles = titles[:max_papers]
            print(f"Processing first {len(titles)} papers...")
        else:
            print(f"Processing all {len(titles)} papers...")

        successful_citations = []
        failed_citations = []

        for i, title in enumerate(titles, 1):
            print(f"\nProcessing {i}/{len(titles)}: {title[:60]}...")

            citation = self.search_citation(title)
            if citation:
                successful_citations.append(citation)
                print(f"✓ Found citation for: {title[:60]}...")
            else:
                failed_citations.append(title)
                print(f"✗ No citation found for: {title[:60]}...")

            # Add delay to avoid rate limiting
            if i < len(titles):  # Don't delay after the last request
                time.sleep(self.delay)

        # Generate output files
        self.save_citations(successful_citations, failed_citations, output_format)

        print(f"\n=== Summary ===")
        print(f"Total papers processed: {len(titles)}")
        print(f"Successful citations: {len(successful_citations)}")
        print(f"Failed citations: {len(failed_citations)}")
        print(f"Success rate: {len(successful_citations)/len(titles)*100:.1f}%")

    def process_csv_citations_enhanced(self, csv_file_path: str, max_papers: int = None,
                                     output_format: str = 'both', use_csv_fallback: bool = True) -> None:
        """
        Process all papers from CSV and generate citations with fallback to CSV data.

        Args:
            csv_file_path: Path to the consolidated papers CSV file
            max_papers: Maximum number of papers to process (None for all)
            output_format: 'ris', 'bibtex', or 'both'
            use_csv_fallback: Use CSV data when scholarly search fails
        """
        print(f"Reading papers from: {csv_file_path}")
        papers = self.read_papers_from_csv(csv_file_path)

        if not papers:
            print("No papers found in the CSV file.")
            return

        # Limit number of papers if specified
        if max_papers:
            papers = papers[:max_papers]
            print(f"Processing first {len(papers)} papers...")
        else:
            print(f"Processing all {len(papers)} papers...")

        successful_citations = []
        csv_fallback_citations = []
        failed_citations = []

        for i, paper in enumerate(papers, 1):
            title = paper.get('title', '')
            print(f"\nProcessing {i}/{len(papers)}: {title[:60]}...")

            # Try scholarly search first
            citation = self.search_citation(title)
            if citation:
                successful_citations.append(citation)
                print(f"✓ Found citation via scholarly for: {title[:60]}...")
            elif use_csv_fallback:
                # Use CSV data as fallback
                csv_citation = self.create_citation_from_csv_data(paper)
                csv_fallback_citations.append(csv_citation)
                print(f"◐ Using CSV data for: {title[:60]}...")
            else:
                failed_citations.append(title)
                print(f"✗ No citation found for: {title[:60]}...")

            # Add delay to avoid rate limiting (only for scholarly searches)
            if i < len(papers):
                time.sleep(self.delay)

        # Combine all citations
        all_citations = successful_citations + csv_fallback_citations

        # Generate output files
        self.save_citations_enhanced(successful_citations, csv_fallback_citations, failed_citations, output_format)

        print(f"\n=== Summary ===")
        print(f"Total papers processed: {len(papers)}")
        print(f"Successful scholarly citations: {len(successful_citations)}")
        print(f"CSV fallback citations: {len(csv_fallback_citations)}")
        print(f"Failed citations: {len(failed_citations)}")
        print(f"Total citations generated: {len(all_citations)}")
        print(f"Overall success rate: {len(all_citations)/len(papers)*100:.1f}%")

    def save_citations(self, successful_citations: List[Dict],
                      failed_citations: List[str], output_format: str = 'both') -> None:
        """
        Save citations to files in specified format(s).

        Args:
            successful_citations: List of successfully found citations
            failed_citations: List of titles that couldn't be found
            output_format: 'ris', 'bibtex', or 'both'
        """
        timestamp = time.strftime("%Y%m%d_%H%M%S")

        if output_format in ['ris', 'both'] and successful_citations:
            ris_filename = f"citations_{timestamp}.ris"
            with open(ris_filename, 'w', encoding='utf-8') as f:
                for citation in successful_citations:
                    f.write(self.format_ris_entry(citation))
            print(f"RIS citations saved to: {ris_filename}")

        if output_format in ['bibtex', 'both'] and successful_citations:
            bibtex_filename = f"citations_{timestamp}.bib"
            with open(bibtex_filename, 'w', encoding='utf-8') as f:
                for i, citation in enumerate(successful_citations):
                    cite_key = f"paper{i+1:03d}"
                    f.write(self.format_bibtex_entry(citation, cite_key))
            print(f"BibTeX citations saved to: {bibtex_filename}")

        # Save failed citations for manual review
        if failed_citations:
            failed_filename = f"failed_citations_{timestamp}.txt"
            with open(failed_filename, 'w', encoding='utf-8') as f:
                f.write("Papers that couldn't be automatically cited:\n\n")
                for i, title in enumerate(failed_citations, 1):
                    f.write(f"{i}. {title}\n")
            print(f"Failed citations saved to: {failed_filename}")

    def save_citations_enhanced(self, successful_citations: List[Dict],
                              csv_citations: List[Dict], failed_citations: List[str],
                              output_format: str = 'both') -> None:
        """
        Save citations to files in specified format(s) with separate sections.

        Args:
            successful_citations: List of successfully found citations via scholarly
            csv_citations: List of citations created from CSV data
            failed_citations: List of titles that couldn't be processed
            output_format: 'ris', 'bibtex', or 'both'
        """
        import os

        # Create results/cite directory if it doesn't exist
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(current_dir)
        cite_dir = os.path.join(project_dir, 'results', 'cite')
        os.makedirs(cite_dir, exist_ok=True)

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        all_citations = successful_citations + csv_citations

        if output_format in ['ris', 'both'] and all_citations:
            ris_filename = os.path.join(cite_dir, f"citations_{timestamp}.ris")
            with open(ris_filename, 'w', encoding='utf-8') as f:
                # Write scholarly citations first
                if successful_citations:
                    f.write("// Citations found via Google Scholar\n\n")
                    for citation in successful_citations:
                        f.write(self.format_ris_entry(citation))

                # Write CSV fallback citations
                if csv_citations:
                    f.write("\n// Citations created from CSV data\n\n")
                    for citation in csv_citations:
                        f.write(self.format_ris_entry(citation))

            print(f"RIS citations saved to: {ris_filename}")

        if output_format in ['bibtex', 'both'] and all_citations:
            bibtex_filename = os.path.join(cite_dir, f"citations_{timestamp}.bib")
            with open(bibtex_filename, 'w', encoding='utf-8') as f:
                # Write scholarly citations first
                ref_counter = 1
                if successful_citations:
                    f.write("% Citations found via Google Scholar\n\n")
                    for citation in successful_citations:
                        cite_key = f"ref{ref_counter}"
                        f.write(self.format_bibtex_entry(citation, cite_key))
                        ref_counter += 1

                # Write CSV fallback citations
                if csv_citations:
                    f.write("\n% Citations created from CSV data\n\n")
                    for citation in csv_citations:
                        cite_key = f"ref{ref_counter}"
                        f.write(self.format_bibtex_entry(citation, cite_key))
                        ref_counter += 1

            print(f"BibTeX citations saved to: {bibtex_filename}")

        # Save failed citations for manual review
        if failed_citations:
            failed_filename = os.path.join(cite_dir, f"failed_citations_{timestamp}.txt")
            with open(failed_filename, 'w', encoding='utf-8') as f:
                f.write("Papers that couldn't be automatically cited:\n\n")
                for i, title in enumerate(failed_citations, 1):
                    f.write(f"{i}. {title}\n")
            print(f"Failed citations saved to: {failed_filename}")


def main():
    """
    Main function to process citations from consolidated_papers.csv
    """
    import os

    # Set up file paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(current_dir)
    csv_file = os.path.join(project_dir, 'results', 'consolidated_papers.csv')

    # Check if CSV file exists
    if not os.path.exists(csv_file):
        print(f"Error: Could not find consolidated_papers.csv at {csv_file}")
        return

    # Initialize citation processor
    processor = CitationProcessor(delay=0.5)  # Faster processing with shorter delay

    # Process citations with enhanced method - ALL PAPERS
    processor.process_csv_citations_enhanced(
        csv_file_path=csv_file,
        max_papers=None,  # Process ALL papers
        output_format='both',  # Generate both RIS and BibTeX formats
        use_csv_fallback=True  # Use CSV data when scholarly search fails
    )


if __name__ == "__main__":
    main()