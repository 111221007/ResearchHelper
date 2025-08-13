import pandas as pd
import requests
import time
import json
from datetime import datetime
import urllib.parse

def confirm_paper_existence(title):
    """
    Confirm if a paper exists using Crossref API
    """
    # URL encode the title for the API call
    encoded_title = urllib.parse.quote(title)
    url = f"https://api.crossref.org/works?query={encoded_title}&rows=5"

    try:
        print(f"Checking: {title}")
        print(f"API URL: {url}")

        response = requests.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()

        if data['status'] == 'ok' and data['message']['total-results'] > 0:
            items = data['message']['items']

            # Check for exact or close matches
            for item in items:
                api_title = item.get('title', [''])[0] if item.get('title') else ''

                # Simple similarity check (can be improved)
                if title.lower() in api_title.lower() or api_title.lower() in title.lower():
                    authors = []
                    if 'author' in item:
                        authors = [f"{author.get('given', '')} {author.get('family', '')}"
                                 for author in item['author']]

                    result = {
                        'found': True,
                        'api_title': api_title,
                        'authors': ', '.join(authors),
                        'published_year': item.get('published-print', {}).get('date-parts', [[None]])[0][0] or
                                        item.get('published-online', {}).get('date-parts', [[None]])[0][0],
                        'journal': item.get('container-title', [''])[0] if item.get('container-title') else '',
                        'doi': item.get('DOI', ''),
                        'publisher': item.get('publisher', ''),
                        'type': item.get('type', ''),
                        'score': item.get('score', 0)
                    }

                    print(f"✅ FOUND: {api_title}")
                    print(f"   Authors: {result['authors']}")
                    print(f"   Year: {result['published_year']}")
                    print(f"   DOI: {result['doi']}")
                    print("-" * 80)

                    return result

            # If no close match found
            print(f"❌ NOT FOUND: No close match for '{title}'")
            print(f"   Top result: {items[0].get('title', [''])[0] if items[0].get('title') else 'No title'}")
            print("-" * 80)

            return {
                'found': False,
                'api_title': items[0].get('title', [''])[0] if items else '',
                'reason': 'No close match found'
            }
        else:
            print(f"❌ NOT FOUND: No results for '{title}'")
            print("-" * 80)
            return {
                'found': False,
                'api_title': '',
                'reason': 'No results returned'
            }

    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR: Failed to query '{title}' - {str(e)}")
        print("-" * 80)
        return {
            'found': False,
            'api_title': '',
            'reason': f'API Error: {str(e)}'
        }
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {str(e)}")
        print("-" * 80)
        return {
            'found': False,
            'api_title': '',
            'reason': f'Unexpected error: {str(e)}'
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

            # Confirm existence
            result = confirm_paper_existence(title)

            # Add original data to result
            result['original_id'] = original_id
            result['original_title'] = title
            result['original_year'] = row['year']
            result['original_venue'] = row['venue']
            result['original_category'] = row['category']

            results.append(result)

            # Rate limiting - be nice to the API
            time.sleep(1)

        # Create results DataFrame
        results_df = pd.DataFrame(results)

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"/Users/reddy/2025/ResearchHelper/results/paper_existence_check_{timestamp}.csv"
        results_df.to_csv(output_path, index=False)

        # Summary
        found_count = sum(1 for r in results if r['found'])
        not_found_count = len(results) - found_count

        print("\n" + "=" * 80)
        print("SUMMARY:")
        print(f"Total papers checked: {len(results)}")
        print(f"Papers found in Crossref: {found_count}")
        print(f"Papers not found: {not_found_count}")
        print(f"Success rate: {(found_count/len(results)*100):.1f}%")
        print(f"\nResults saved to: {output_path}")
        print("=" * 80)

        # Show papers not found
        if not_found_count > 0:
            print("\nPAPERS NOT FOUND:")
            for result in results:
                if not result['found']:
                    print(f"- {result['original_title']} (Reason: {result['reason']})")

    except FileNotFoundError:
        print(f"❌ Error: Could not find file {csv_path}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main()
