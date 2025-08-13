import pandas as pd
import requests
import time
import json
from datetime import datetime
import urllib.parse

def get_paper_tldr_from_semantic_scholar(title):
    """
    Get TL;DR summary for a paper using Semantic Scholar API
    """
    try:
        # First, search for the paper by title
        search_url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            'query': title,
            'limit': 5,
            'fields': 'paperId,title,abstract,tldr,year,authors,venue,url'
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
                    tldr_text = ''
                    abstract_text = ''
                    
                    # Get TL;DR if available
                    if paper.get('tldr') and paper['tldr'].get('text'):
                        tldr_text = paper['tldr']['text']
                    
                    # Get abstract if available
                    if paper.get('abstract'):
                        abstract_text = paper['abstract']
                    
                    # Get authors
                    authors = []
                    if paper.get('authors'):
                        authors = [author.get('name', '') for author in paper['authors']]
                    
                    result = {
                        'found': True,
                        'paper_id': paper.get('paperId', ''),
                        'semantic_title': paper_title,
                        'tldr': tldr_text,
                        'abstract': abstract_text,
                        'authors': ', '.join(authors),
                        'year': paper.get('year', ''),
                        'venue': paper.get('venue', ''),
                        'url': paper.get('url', ''),
                        'api_response': 'Success'
                    }
                    
                    print(f"✅ FOUND: {paper_title}")
                    if tldr_text:
                        print(f"   TL;DR: {tldr_text[:100]}...")
                    else:
                        print(f"   TL;DR: Not available")
                    if abstract_text:
                        print(f"   Abstract: {abstract_text[:100]}...")
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
                'tldr': '',
                'abstract': '',
                'authors': '',
                'year': '',
                'venue': '',
                'url': '',
                'api_response': 'No close match found'
            }
        else:
            print(f"❌ NOT FOUND: No results for '{title}'")
            print("-" * 80)
            return {
                'found': False,
                'paper_id': '',
                'semantic_title': '',
                'tldr': '',
                'abstract': '',
                'authors': '',
                'year': '',
                'venue': '',
                'url': '',
                'api_response': 'No results returned'
            }
            
    except requests.exceptions.RequestException as e:
        print(f"❌ API ERROR: Failed to query '{title}' - {str(e)}")
        print("-" * 80)
        return {
            'found': False,
            'paper_id': '',
            'semantic_title': '',
            'tldr': '',
            'abstract': '',
            'authors': '',
            'year': '',
            'venue': '',
            'url': '',
            'api_response': f'API Error: {str(e)}'
        }
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {str(e)}")
        print("-" * 80)
        return {
            'found': False,
            'paper_id': '',
            'semantic_title': '',
            'tldr': '',
            'abstract': '',
            'authors': '',
            'year': '',
            'venue': '',
            'url': '',
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
            
            # Get TL;DR from Semantic Scholar
            result = get_paper_tldr_from_semantic_scholar(title)
            
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
            'tldr', 'abstract', 'authors', 'original_year', 'year',
            'original_venue', 'venue', 'original_category', 'original_keywords',
            'paper_id', 'url', 'api_response'
        ]
        
        # Only include columns that exist
        existing_columns = [col for col in columns_order if col in results_df.columns]
        results_df = results_df[existing_columns]
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"/Users/reddy/2025/ResearchHelper/results/papers_tldr_semantic_scholar_{timestamp}.csv"
        results_df.to_csv(output_path, index=False)
        
        # Summary
        found_count = sum(1 for r in results if r['found'])
        tldr_count = sum(1 for r in results if r['found'] and r['tldr'])
        abstract_count = sum(1 for r in results if r['found'] and r['abstract'])
        not_found_count = len(results) - found_count
        
        print("\n" + "=" * 80)
        print("SUMMARY:")
        print(f"Total papers processed: {len(results)}")
        print(f"Papers found in Semantic Scholar: {found_count}")
        print(f"Papers with TL;DR: {tldr_count}")
        print(f"Papers with Abstract: {abstract_count}")
        print(f"Papers not found: {not_found_count}")
        print(f"Success rate: {(found_count/len(results)*100):.1f}%")
        print(f"TL;DR availability: {(tldr_count/len(results)*100):.1f}%")
        print(f"\nResults saved to: {output_path}")
        print("=" * 80)
        
        # Show some statistics
        if tldr_count > 0:
            print(f"\nSample TL;DR entries:")
            tldr_results = [r for r in results if r['found'] and r['tldr']][:3]
            for i, result in enumerate(tldr_results, 1):
                print(f"{i}. {result['original_title'][:60]}...")
                print(f"   TL;DR: {result['tldr']}")
                print()
        
    except FileNotFoundError:
        print(f"❌ Error: Could not find file {csv_path}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main()
