#!/usr/bin/env python3
"""
Test abstracts with simple title query format
"""

import requests
import json
from urllib.parse import quote

def test_paper_abstract(title, test_type=""):
    """Test a specific paper for abstract availability"""
    base_url = "https://api.crossref.org/works"
    headers = {'User-Agent': 'ResearchHelper/1.0 (mailto:researcher@example.com)'}

    print(f"\n📝 Testing: {title[:60]}...")
    print(f"🧪 Test Type: {test_type}")

    try:
        if test_type == "simple":
            # Simple format: just the title without quotes or encoding
            url = f"{base_url}?query.title={title}"
        elif test_type == "encoded":
            # URL encoded but no quotes
            encoded_title = quote(title)
            url = f"{base_url}?query.title={encoded_title}"
        elif test_type == "quoted":
            # Our current method with quotes
            clean_title = title.replace('"', '').replace("'", "")
            encoded_title = quote(clean_title)
            url = f"{base_url}?query.title=\"{encoded_title}\"&rows=3"
        elif test_type == "basic_query":
            # Very basic query format
            url = f"{base_url}?query={title}"

        print(f"🌐 API URL: {url}")

        response = requests.get(url, headers=headers, timeout=15)
        data = response.json()
        items = data.get('message', {}).get('items', [])

        if items:
            first_item = items[0]
            item_title = first_item.get('title', ['No title'])[0] if first_item.get('title') else 'No title'
            publisher = first_item.get('publisher', 'Unknown')
            has_abstract = 'abstract' in first_item and first_item['abstract']

            print(f"✅ Found match")
            print(f"📝 Title: {item_title[:60]}...")
            print(f"🏢 Publisher: {publisher}")
            print(f"📄 Has Abstract: {'✅ YES' if has_abstract else '❌ NO'}")

            if has_abstract:
                abstract = str(first_item['abstract'])
                print(f"📏 Abstract Length: {len(abstract)}")
                print(f"📄 Preview: {abstract[:200]}...")

                # Check format
                if '<jats:' in abstract or '&lt;' in abstract:
                    print(f"🏷️  Format: JATS XML")
                else:
                    print(f"🏷️  Format: Plain text")

            return has_abstract
        else:
            print(f"❌ No matches found")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("🧪 TESTING DIFFERENT API QUERY FORMATS")
    print("="*80)

    # Test with the paper that we know should have abstract
    title = "FaaSCtrl: A Comprehensive-Latency Controller for Serverless Platforms"

    # Test different query formats
    formats = [
        ("simple", "Simple title without encoding"),
        ("encoded", "URL encoded title without quotes"),
        ("quoted", "Current method with quotes"),
        ("basic_query", "Basic query parameter")
    ]

    results = []
    for format_type, description in formats:
        print(f"\n{'='*60}")
        print(f"🔬 Testing: {description}")
        print(f"{'='*60}")

        has_abstract = test_paper_abstract(title, format_type)
        results.append((format_type, description, has_abstract))

    print(f"\n{'='*80}")
    print("📊 SUMMARY OF RESULTS")
    print("="*80)

    for format_type, description, has_abstract in results:
        status = "✅ HAS ABSTRACT" if has_abstract else "❌ NO ABSTRACT"
        print(f"{status} | {format_type:<15} | {description}")

    # Test with a few more titles using the best format
    print(f"\n{'='*80}")
    print("🔍 TESTING OTHER TITLES WITH SIMPLE FORMAT")
    print("="*80)

    other_titles = [
        "Serverless computing: A survey of opportunities, challenges, and applications",
        "Cold start in serverless computing: Current trends",
        "Performance evaluation of serverless computing platforms"
    ]

    for test_title in other_titles:
        test_paper_abstract(test_title, "simple")

if __name__ == "__main__":
    main()
