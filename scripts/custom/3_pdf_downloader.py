import pandas as pd
import requests
import time
import json
import os
from datetime import datetime
import urllib.parse
from pathlib import Path

def download_pdf_from_semantic_scholar(title):
    """
    Check for PDF availability and download from Semantic Scholar API
    """
    try:
        # First, search for the paper by title
        search_url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            'query': title,
            'limit': 5,
            'fields': 'paperId,title,abstract,year,authors,venue,url,openAccessPdf,isOpenAccess'
        }

        print(f"Searching: {title}")
        print(f"API URL: {search_url}")

        response = requests.get(search_url, params=params, timeout=15)
        response.raise_for_status()

        data = response.json()

        if 'data' in data and len(data['data']) > 0:
            # Look for the best match
            for paper in data['data']:
                paper_title = paper.get('title', '')

                # Check for close match
                if title.lower() in paper_title.lower() or paper_title.lower() in title.lower():
                    pdf_url = ''
                    pdf_downloaded = False
                    pdf_filename = ''

                    # Check for open access PDF
                    if paper.get('openAccessPdf') and paper['openAccessPdf'].get('url'):
                        pdf_url = paper['openAccessPdf']['url']

                        # Create safe filename
                        safe_title = "".join(c for c in paper_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                        safe_title = safe_title[:100]  # Limit length
                        pdf_filename = f"{safe_title}.pdf"

                        # Create pdfs directory if it doesn't exist
                        pdf_dir = "/Users/reddy/2025/ResearchHelper/results/pdf"
                        os.makedirs(pdf_dir, exist_ok=True)
                        pdf_path = os.path.join(pdf_dir, pdf_filename)

                        try:
                            # Download PDF
                            print(f"   📥 Downloading PDF: {pdf_url}")
                            pdf_response = requests.get(pdf_url, timeout=30)
                            pdf_response.raise_for_status()

                            with open(pdf_path, 'wb') as f:
                                f.write(pdf_response.content)

                            pdf_downloaded = True
                            print(f"   ✅ PDF downloaded: {pdf_filename}")

                        except Exception as download_error:
                            print(f"   ❌ PDF download failed: {str(download_error)}")

                    # Get authors
                    authors = []
                    if paper.get('authors'):
                        authors = [author.get('name', '') for author in paper['authors']]

                    result = {
                        'found': True,
                        'paper_id': paper.get('paperId', ''),
                        'semantic_title': paper_title,
                        'authors': ', '.join(authors),
                        'year': paper.get('year', ''),
                        'venue': paper.get('venue', ''),
                        'url': paper.get('url', ''),
                        'is_open_access': paper.get('isOpenAccess', False),
                        'pdf_url': pdf_url,
                        'pdf_available': bool(pdf_url),
                        'pdf_downloaded': pdf_downloaded,
                        'pdf_filename': pdf_filename if pdf_downloaded else '',
                        'api_response': 'Success'
                    }

                    print(f"✅ FOUND: {paper_title}")
                    print(f"   Open Access: {paper.get('isOpenAccess', False)}")
                    print(f"   PDF Available: {bool(pdf_url)}")
                    if pdf_url:
                        print(f"   PDF URL: {pdf_url}")
                    print("-" * 80)

                    return result

            # If no close match found
            print(f"❌ NO CLOSE MATCH: '{title}'")
            print(f"   Top result: {data['data'][0].get('title', 'No title')}")
            print("-" * 80)

            return {
                'found': False,
                'paper_id': '',
                'semantic_title': data['data'][0].get('title', '') if data['data'] else '',
                'authors': '',
                'year': '',
                'venue': '',
                'url': '',
                'is_open_access': False,
                'pdf_url': '',
                'pdf_available': False,
                'pdf_downloaded': False,
                'pdf_filename': '',
                'api_response': 'No close match found'
            }
        else:
            print(f"❌ NOT FOUND: No results for '{title}'")
            print("-" * 80)
            return {
                'found': False,
                'paper_id': '',
                'semantic_title': '',
                'authors': '',
                'year': '',
                'venue': '',
                'url': '',
                'is_open_access': False,
                'pdf_url': '',
                'pdf_available': False,
                'pdf_downloaded': False,
                'pdf_filename': '',
                'api_response': 'No results returned'
            }

    except requests.exceptions.RequestException as e:
        print(f"❌ API ERROR: Failed to query '{title}' - {str(e)}")
        print("-" * 80)
        return {
            'found': False,
            'paper_id': '',
            'semantic_title': '',
            'authors': '',
            'year': '',
            'venue': '',
            'url': '',
            'is_open_access': False,
            'pdf_url': '',
            'pdf_available': False,
            'pdf_downloaded': False,
            'pdf_filename': '',
            'api_response': f'API Error: {str(e)}'
        }
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {str(e)}")
        print("-" * 80)
        return {
            'found': False,
            'paper_id': '',
            'semantic_title': '',
            'authors': '',
            'year': '',
            'venue': '',
            'url': '',
            'is_open_access': False,
            'pdf_url': '',
            'pdf_available': False,
            'pdf_downloaded': False,
            'pdf_filename': '',
            'api_response': f'Unexpected error: {str(e)}'
        }

def main():
    # Read the consolidated papers CSV
    csv_path = "/Users/reddy/2025/ResearchHelper/results/consolidated_papers.csv"

    try:
        df = pd.read_csv(csv_path)
        print(f"Loaded {len(df)} papers from {csv_path}")
        print("=" * 80)

        # Prepare results list
        results = []

        # Process each title
        for index, row in df.iterrows():
            title = row['title']
            original_id = row['consolidated_id']

            print(f"\n[{index + 1}/{len(df)}] Processing Paper ID: {original_id}")

            # Check for PDF and download if available
            result = download_pdf_from_semantic_scholar(title)

            # Add original data to result
            result['original_id'] = original_id
            result['original_title'] = title
            result['original_year'] = row['year']
            result['original_venue'] = row['venue']
            result['original_category'] = row['category']
            result['original_keywords'] = row['keywords']

            results.append(result)

            # Rate limiting - be respectful to the API
            time.sleep(2)  # 2 seconds between requests

        # Create results DataFrame
        results_df = pd.DataFrame(results)

        # Reorder columns for better readability
        columns_order = [
            'original_id', 'original_title', 'semantic_title', 'found',
            'pdf_available', 'pdf_downloaded', 'pdf_filename', 'pdf_url',
            'is_open_access', 'authors', 'original_year', 'year',
            'original_venue', 'venue', 'original_category', 'original_keywords',
            'paper_id', 'url', 'api_response'
        ]

        # Only include columns that exist
        existing_columns = [col for col in columns_order if col in results_df.columns]
        results_df = results_df[existing_columns]

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"/Users/reddy/2025/ResearchHelper/results/papers_pdf_download_{timestamp}.csv"
        results_df.to_csv(output_path, index=False)

        # Summary
        found_count = sum(1 for r in results if r['found'])
        pdf_available_count = sum(1 for r in results if r['pdf_available'])
        pdf_downloaded_count = sum(1 for r in results if r['pdf_downloaded'])
        not_found_count = len(results) - found_count

        print("\n" + "=" * 80)
        print("SUMMARY:")
        print(f"Total papers processed: {len(results)}")
        print(f"Papers found in Semantic Scholar: {found_count}")
        print(f"Papers with PDF available: {pdf_available_count}")
        print(f"Papers with PDF downloaded: {pdf_downloaded_count}")
        print(f"Papers not found: {not_found_count}")
        print(f"Success rate: {(found_count/len(results)*100):.1f}%")
        print(f"PDF availability rate: {(pdf_available_count/len(results)*100):.1f}%")
        print(f"PDF download rate: {(pdf_downloaded_count/len(results)*100):.1f}%")
        print(f"\nResults saved to: {output_path}")
        print("=" * 80)

        # Show some statistics
        if pdf_downloaded_count > 0:
            print(f"\nSample downloaded PDFs:")
            downloaded_results = [r for r in results if r['pdf_downloaded']][:3]
            for i, result in enumerate(downloaded_results, 1):
                print(f"{i}. {result['original_title'][:60]}...")
                print(f"   PDF: {result['pdf_filename']}")
                print()

    except FileNotFoundError:
        print(f"❌ Error: Could not find file {csv_path}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main()
