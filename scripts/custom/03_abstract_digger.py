import pandas as pd
import requests
import time
import json
import os
from datetime import datetime
import urllib.parse
import re
from bs4 import BeautifulSoup
import random
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET

def get_robust_session():
    """Create a robust requests session with headers"""
    session = requests.Session()

    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ]

    session.headers.update({
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    })

    return session

def search_semantic_scholar_abstract(title, year=None):
    """Search Semantic Scholar for paper abstract"""
    try:
        session = get_robust_session()

        search_url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            'query': title,
            'limit': 5,
            'fields': 'paperId,title,abstract,year,authors,venue'
        }

        print(f"   🔍 Searching Semantic Scholar...")
        time.sleep(random.uniform(3, 6))  # Rate limiting

        response = session.get(search_url, params=params, timeout=20)

        if response.status_code == 429:
            print(f"   ⏳ Rate limited, waiting...")
            time.sleep(30)
            response = session.get(search_url, params=params, timeout=20)

        if response.status_code == 200:
            data = response.json()

            if 'data' in data and len(data['data']) > 0:
                for paper in data['data']:
                    paper_title = paper.get('title', '').lower()
                    search_title = title.lower()

                    # Check title similarity
                    title_words = set(search_title.split())
                    paper_words = set(paper_title.split())
                    common_words = title_words.intersection(paper_words)

                    if (len(common_words) >= 3 or
                        search_title in paper_title or
                        paper_title in search_title):

                        # Check year if provided
                        if year and paper.get('year'):
                            if abs(int(year) - int(paper['year'])) > 1:
                                continue

                        abstract = paper.get('abstract', '').strip()
                        if abstract and len(abstract) > 50:
                            print(f"   ✅ Found abstract ({len(abstract)} chars)")
                            return {
                                'source': 'Semantic Scholar',
                                'abstract': abstract,
                                'confidence': 'high'
                            }

        return {'source': 'Semantic Scholar', 'abstract': '', 'confidence': 'none'}

    except Exception as e:
        print(f"   ❌ Semantic Scholar error: {str(e)}")
        return {'source': 'Semantic Scholar', 'abstract': '', 'confidence': 'error'}

def search_arxiv_abstract(title):
    """Search arXiv for paper abstract"""
    try:
        session = get_robust_session()

        # Clean title for search
        clean_title = re.sub(r'[^\w\s]', ' ', title).strip()
        search_terms = ' '.join(clean_title.split()[:8])  # First 8 words

        arxiv_url = "http://export.arxiv.org/api/query"
        params = {
            'search_query': f'all:"{search_terms}"',
            'start': 0,
            'max_results': 10
        }

        print(f"   🔍 Searching arXiv...")
        response = session.get(arxiv_url, params=params, timeout=15)

        if response.status_code == 200:
            root = ET.fromstring(response.content)

            for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
                arxiv_title = entry.find('{http://www.w3.org/2005/Atom}title').text.strip()

                # Check title similarity
                title_words = set(title.lower().split())
                arxiv_words = set(arxiv_title.lower().split())
                common_words = title_words.intersection(arxiv_words)

                if len(common_words) >= 3:
                    summary_elem = entry.find('{http://www.w3.org/2005/Atom}summary')
                    if summary_elem is not None:
                        abstract = summary_elem.text.strip()
                        if abstract and len(abstract) > 50:
                            print(f"   ✅ Found abstract ({len(abstract)} chars)")
                            return {
                                'source': 'arXiv',
                                'abstract': abstract,
                                'confidence': 'high'
                            }

        return {'source': 'arXiv', 'abstract': '', 'confidence': 'none'}

    except Exception as e:
        print(f"   ❌ arXiv error: {str(e)}")
        return {'source': 'arXiv', 'abstract': '', 'confidence': 'error'}

def search_dblp_abstract(title):
    """Search DBLP for paper information"""
    try:
        session = get_robust_session()

        # Clean title for search
        clean_title = urllib.parse.quote(title[:100])
        dblp_url = f"https://dblp.org/search/publ/api?q={clean_title}&format=json"

        print(f"   🔍 Searching DBLP...")
        time.sleep(1)
        response = session.get(dblp_url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            hits = data.get('result', {}).get('hits', {}).get('hit', [])

            for hit in hits[:3]:  # Check top 3 results
                info = hit.get('info', {})
                dblp_title = info.get('title', '').lower()

                # Check title similarity
                if (title.lower() in dblp_title or
                    dblp_title in title.lower() or
                    len(set(title.lower().split()).intersection(set(dblp_title.split()))) >= 3):

                    # DBLP doesn't have abstracts, but we can get DOI for further lookup
                    doi = info.get('doi', '')
                    if doi:
                        return search_doi_abstract(doi)

        return {'source': 'DBLP', 'abstract': '', 'confidence': 'none'}

    except Exception as e:
        print(f"   ❌ DBLP error: {str(e)}")
        return {'source': 'DBLP', 'abstract': '', 'confidence': 'error'}

def search_doi_abstract(doi):
    """Search using DOI to get abstract from CrossRef"""
    try:
        session = get_robust_session()

        crossref_url = f"https://api.crossref.org/works/{doi}"

        print(f"   🔍 Searching CrossRef with DOI...")
        response = session.get(crossref_url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            message = data.get('message', {})
            abstract = message.get('abstract', '')

            if abstract and len(abstract) > 50:
                # Clean HTML tags if present
                abstract = re.sub(r'<[^>]+>', '', abstract)
                print(f"   ✅ Found abstract ({len(abstract)} chars)")
                return {
                    'source': 'CrossRef',
                    'abstract': abstract.strip(),
                    'confidence': 'high'
                }

        return {'source': 'CrossRef', 'abstract': '', 'confidence': 'none'}

    except Exception as e:
        print(f"   ❌ CrossRef error: {str(e)}")
        return {'source': 'CrossRef', 'abstract': '', 'confidence': 'error'}

def search_google_scholar_abstract(title):
    """Search Google Scholar for abstract (basic scraping)"""
    try:
        session = get_robust_session()

        # Construct search query
        search_query = f'"{title}"'
        google_url = "https://scholar.google.com/scholar"
        params = {
            'q': search_query,
            'hl': 'en'
        }

        print(f"   🔍 Searching Google Scholar...")
        time.sleep(random.uniform(3, 7))  # Longer delay for Google

        response = session.get(google_url, params=params, timeout=15)

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            for result in soup.find_all('div', class_='gs_r'):
                # Look for the abstract/description
                abstract_elem = result.find('div', class_='gs_rs')
                if abstract_elem:
                    abstract = abstract_elem.get_text().strip()
                    if abstract and len(abstract) > 50:
                        print(f"   ✅ Found abstract ({len(abstract)} chars)")
                        return {
                            'source': 'Google Scholar',
                            'abstract': abstract,
                            'confidence': 'medium'
                        }

        return {'source': 'Google Scholar', 'abstract': '', 'confidence': 'none'}

    except Exception as e:
        print(f"   ❌ Google Scholar error: {str(e)}")
        return {'source': 'Google Scholar', 'abstract': '', 'confidence': 'error'}

def search_acm_ieee_abstract(title, venue):
    """Search ACM or IEEE digital libraries"""
    try:
        session = get_robust_session()

        # Determine if it's ACM or IEEE based on venue
        if any(keyword in venue.lower() for keyword in ['acm', 'sigcomm', 'sigkdd', 'socc']):
            # Try ACM Digital Library
            acm_search_url = "https://dl.acm.org/action/doSearch"
            params = {'AllField': title}

            print(f"   🔍 Searching ACM Digital Library...")
            response = session.get(acm_search_url, params=params, timeout=10)

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')

                # Look for abstract in search results
                for abstract_elem in soup.find_all('div', class_='issue-item__abstract'):
                    abstract = abstract_elem.get_text().strip()
                    if abstract and len(abstract) > 50:
                        print(f"   ✅ Found abstract ({len(abstract)} chars)")
                        return {
                            'source': 'ACM Digital Library',
                            'abstract': abstract,
                            'confidence': 'high'
                        }

        elif any(keyword in venue.lower() for keyword in ['ieee', 'infocom', 'icdcs']):
            # Try IEEE Xplore
            ieee_search_url = "https://ieeexplore.ieee.org/search/searchresult.jsp"
            params = {'queryText': title}

            print(f"   🔍 Searching IEEE Xplore...")
            response = session.get(ieee_search_url, params=params, timeout=10)

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')

                # Look for abstract in search results
                for abstract_elem in soup.find_all('div', class_='description'):
                    abstract = abstract_elem.get_text().strip()
                    if abstract and len(abstract) > 50:
                        print(f"   ✅ Found abstract ({len(abstract)} chars)")
                        return {
                            'source': 'IEEE Xplore',
                            'abstract': abstract,
                            'confidence': 'high'
                        }

        return {'source': 'ACM/IEEE', 'abstract': '', 'confidence': 'none'}

    except Exception as e:
        print(f"   ❌ ACM/IEEE error: {str(e)}")
        return {'source': 'ACM/IEEE', 'abstract': '', 'confidence': 'error'}

def extract_abstract_comprehensive(title, year=None, venue=None):
    """Extract abstract using all available sources"""
    print(f"🔍 Searching for abstract: {title[:60]}...")

    sources = [
        ('Semantic Scholar', lambda: search_semantic_scholar_abstract(title, year)),
        ('arXiv', lambda: search_arxiv_abstract(title)),
        ('ACM/IEEE', lambda: search_acm_ieee_abstract(title, venue or '')),
        ('DBLP', lambda: search_dblp_abstract(title)),
        ('Google Scholar', lambda: search_google_scholar_abstract(title))
    ]

    for source_name, search_func in sources:
        try:
            result = search_func()

            if result['abstract'] and len(result['abstract']) > 50:
                return {
                    'abstract': result['abstract'],
                    'source': result['source'],
                    'confidence': result['confidence'],
                    'found': True
                }

            # Rate limiting between sources
            time.sleep(2)

        except Exception as e:
            print(f"   ❌ {source_name} failed: {str(e)}")
            continue

    return {
        'abstract': '',
        'source': 'None',
        'confidence': 'none',
        'found': False
    }

def main():
    """Main function to process all papers and extract abstracts"""

    # Ask user for the input CSV file path
    print("=" * 80)
    print("ABSTRACT DIGGER - CSV Path Selection")
    print("=" * 80)

    while True:
        input_path = input("\nEnter the full path to your CSV file: ").strip()

        # Remove quotes if user copied path with quotes
        input_path = input_path.strip('"').strip("'")

        if os.path.exists(input_path):
            if input_path.endswith('.csv'):
                print(f"✅ Valid CSV file found: {input_path}")
                break
            else:
                print("❌ Error: File must be a CSV file (.csv extension)")
        else:
            print("❌ Error: File not found. Please check the path and try again.")
            print("   Example: /Users/reddy/Downloads/UDPATED_11_AUG_8AM/combined_papers_deduplicated_20250811_081923.csv")

    try:
        df = pd.read_csv(input_path)

        print(f"\nLoaded {len(df)} papers from: {os.path.basename(input_path)}")
        print("Starting comprehensive abstract extraction...")
        print("=" * 80)

        # Check if the CSV has the expected columns
        required_columns = ['title']
        optional_columns = ['year', 'venue', 'journal']

        if 'title' not in df.columns:
            print("❌ Error: CSV must contain a 'title' column")
            return

        print(f"📋 CSV columns found: {list(df.columns)}")

        # Use different ID column names depending on what's available
        id_column = None
        for col in ['paper_id', 'consolidated_id', 'id']:
            if col in df.columns:
                id_column = col
                break

        if not id_column:
            # Create a temporary ID column
            df['temp_id'] = range(1, len(df) + 1)
            id_column = 'temp_id'
            print("📝 No ID column found, created temporary IDs")

        # Add new columns for abstract data
        df['abstract'] = ''
        df['abstract_source'] = ''
        df['abstract_confidence'] = ''

        results = []
        successful_extractions = 0

        # Process in batches to avoid overwhelming APIs
        batch_size = 10
        total_batches = (len(df) + batch_size - 1) // batch_size

        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(df))
            batch_papers = df.iloc[start_idx:end_idx]

            print(f"\n📦 Processing batch {batch_num + 1}/{total_batches} ({len(batch_papers)} papers)")

            for idx, (_, row) in enumerate(batch_papers.iterrows()):
                paper_id = row[id_column]
                title = row['title']
                year = row.get('year', None)
                venue = row.get('venue', row.get('journal', ''))

                print(f"\n[{start_idx + idx + 1}/{len(df)}] Paper ID: {paper_id}")

                # Extract abstract
                result = extract_abstract_comprehensive(title, year, venue)

                if result['found']:
                    successful_extractions += 1
                    df.loc[df[id_column] == paper_id, 'abstract'] = result['abstract']
                    df.loc[df[id_column] == paper_id, 'abstract_source'] = result['source']
                    df.loc[df[id_column] == paper_id, 'abstract_confidence'] = result['confidence']
                    print(f"   ✅ Abstract extracted from {result['source']}")
                else:
                    df.loc[df[id_column] == paper_id, 'abstract'] = 'Not found'
                    df.loc[df[id_column] == paper_id, 'abstract_source'] = 'None'
                    df.loc[df[id_column] == paper_id, 'abstract_confidence'] = 'none'
                    print(f"   ❌ No abstract found")

                # Rate limiting between papers
                time.sleep(3)

            # Longer break between batches
            if batch_num < total_batches - 1:
                print(f"\n⏸️  Break between batches (60 seconds)...")
                time.sleep(60)

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create output filename based on input filename
        input_basename = os.path.splitext(os.path.basename(input_path))[0]
        output_filename = f"{input_basename}_with_abstracts_{timestamp}.csv"
        output_dir = os.path.dirname(input_path)
        output_path = os.path.join(output_dir, output_filename)

        df.to_csv(output_path, index=False)

        print("\n" + "=" * 80)
        print("ABSTRACT EXTRACTION SUMMARY:")
        print(f"Total papers processed: {len(df)}")
        print(f"Abstracts found: {successful_extractions}")
        print(f"Success rate: {(successful_extractions/len(df)*100):.1f}%")
        print(f"Results saved to: {output_path}")
        print("=" * 80)

        # Show source breakdown
        source_counts = df['abstract_source'].value_counts()
        if len(source_counts) > 0:
            print(f"\n📊 Abstract sources breakdown:")
            for source, count in source_counts.items():
                if source != 'None':
                    print(f"   {source}: {count} abstracts")

        # Show confidence breakdown
        confidence_counts = df['abstract_confidence'].value_counts()
        if len(confidence_counts) > 0:
            print(f"\n🎯 Confidence levels:")
            for confidence, count in confidence_counts.items():
                if confidence != 'none':
                    print(f"   {confidence}: {count} abstracts")

        # Show sample abstracts
        successful_papers = df[df['abstract_confidence'] != 'none']
        if len(successful_papers) > 0:
            print(f"\n📝 Sample abstracts:")
            for i, (_, row) in enumerate(successful_papers.head(3).iterrows(), 1):
                print(f"{i}. {row['title'][:50]}...")
                print(f"   Source: {row['abstract_source']}")
                print(f"   Abstract: {row['abstract'][:150]}...")
                print()

    except FileNotFoundError:
        print(f"❌ Error: Could not find file {input_path}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main()
