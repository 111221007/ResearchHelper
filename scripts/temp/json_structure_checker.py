#!/usr/bin/env python3
"""
JSON Structure Checker for Crossref API
This script will show the complete JSON structure returned by Crossref API
"""

import requests
import json
from urllib.parse import quote

def get_json_structure(title, test_name, additional_params=""):
    """
    Get and display the JSON structure from Crossref API
    """
    base_url = "https://api.crossref.org/works"
    headers = {
        'User-Agent': 'ResearchHelper/1.0 (mailto:researcher@example.com)'
    }

    # Clean and encode the title for URL
    clean_title = title.replace('"', '').replace("'", "")
    encoded_title = quote(clean_title)

    # Build API URL
    url = f"{base_url}?query.title=\"{encoded_title}\"{additional_params}"

    print(f"\n{'='*80}")
    print(f"🔬 TEST: {test_name}")
    print(f"{'='*80}")
    print(f"🔍 Searching for: {title}")
    print(f"🌐 API URL: {url}")
    print("=" * 80)

    try:
        # Make API request
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        data = response.json()

        # Extract and analyze items
        items = data.get('message', {}).get('items', [])
        total_results = data.get('message', {}).get('total-results', 0)

        print(f"📊 API Response Summary:")
        print(f"  - Total results: {total_results}")
        print(f"  - Items returned: {len(items)}")

        if items:
            print(f"\n🔎 FIRST ITEM ANALYSIS:")
            print("=" * 60)

            first_item = items[0]

            # Show key information
            item_title = first_item.get('title', ['No title'])[0] if first_item.get('title') else 'No title'
            print(f"📝 Title: {item_title}")
            print(f"📅 Year: {first_item.get('published-print', {}).get('date-parts', [[None]])[0][0] if first_item.get('published-print') else 'Unknown'}")
            print(f"📖 Journal: {first_item.get('container-title', ['Unknown'])[0] if first_item.get('container-title') else 'Unknown'}")

            # Check specifically for abstract
            print(f"\n📄 ABSTRACT FIELD ANALYSIS:")
            if 'abstract' in first_item:
                abstract = first_item['abstract']
                print(f"  ✅ Abstract exists: True")
                print(f"  📝 Abstract type: {type(abstract)}")

                if abstract:
                    abstract_str = str(abstract)
                    print(f"  📏 Abstract length: {len(abstract_str)}")
                    print(f"  📄 Abstract preview (first 200 chars):")
                    print(f"     {abstract_str[:200]}...")

                    # Check if it's JATS XML format
                    if '<jats:' in abstract_str or '&lt;' in abstract_str:
                        print(f"  🏷️  Format: JATS XML detected")
                    else:
                        print(f"  🏷️  Format: Plain text")
                else:
                    print(f"  ❌ Abstract is empty/null")
            else:
                print(f"  ❌ Abstract field: NOT FOUND")

            # Show all available keys for reference
            print(f"\n📋 All available keys in response:")
            for key in sorted(first_item.keys()):
                print(f"  - {key}")

        else:
            print("❌ No items found in response")

        return len(items) > 0 and 'abstract' in items[0] and items[0]['abstract']

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    # Test with a title that should have an abstract
    title = "FaaSCtrl: A Comprehensive-Latency Controller for Serverless Platforms"

    print("🧪 TESTING DIFFERENT API PARAMETERS")
    print("="*80)

    # Test 1: With rows=1&sort=relevance (your current failing approach)
    result1 = get_json_structure(title, "With &rows=1&sort=relevance", "&rows=1&sort=relevance")

    # Test 2: Without any additional parameters
    result2 = get_json_structure(title, "Without additional parameters", "")

    # Test 3: With just rows=5
    result3 = get_json_structure(title, "With &rows=5 only", "&rows=5")

    # Test 4: With rows=10&sort=score
    result4 = get_json_structure(title, "With &rows=10&sort=score", "&rows=10&sort=score")

    print(f"\n{'='*80}")
    print("📊 SUMMARY OF RESULTS:")
    print("="*80)
    print(f"Test 1 (rows=1&sort=relevance): {'✅ Found abstract' if result1 else '❌ No abstract'}")
    print(f"Test 2 (no additional params): {'✅ Found abstract' if result2 else '❌ No abstract'}")
    print(f"Test 3 (rows=5 only): {'✅ Found abstract' if result3 else '❌ No abstract'}")
    print(f"Test 4 (rows=10&sort=score): {'✅ Found abstract' if result4 else '❌ No abstract'}")

    print(f"\n✅ Analysis complete!")

if __name__ == "__main__":
    main()
