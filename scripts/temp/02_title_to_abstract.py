#!/usr/bin/env python3
"""
Title to Abstract Fetcher
Reads a CSV file with titles and fetches abstracts from Crossref API
Adds abstract column to the existing CSV
"""

import pandas as pd
import requests
import time
import os
import re
import logging
from datetime import datetime
from typing import Optional
from urllib.parse import quote
import argparse


class TitleToAbstractFetcher:
    """
    Fetches abstracts for paper titles using Crossref API
    """

    def __init__(self):
        self.base_url = "https://api.crossref.org/works"
        self.headers = {
            'User-Agent': 'ResearchHelper/1.0 (mailto:researcher@example.com)'
        }
        self.success_count = 0
        self.failed_count = 0
        self.failed_titles = []

        # Setup API logging
        self.setup_api_logging()

    def setup_api_logging(self):
        """Setup logging for API calls"""
        # Create logs directory if it doesn't exist
        logs_dir = "logs"
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)

        # Setup logger
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"logs/api_calls_{timestamp}.log"

        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename),
                logging.StreamHandler()  # Also log to console
            ]
        )

        self.logger = logging.getLogger(__name__)
        self.logger.info("=" * 60)
        self.logger.info("API Logging Started - Title to Abstract Fetcher")
        self.logger.info("=" * 60)

    def log_api_call(self, url: str, response_time: float, status_code: int,
                     title: str, success: bool, error: str = None):
        """Log API call details"""
        log_message = (
            f"API_CALL | "
            f"URL: {url} | "
            f"Response_Time: {response_time:.2f}s | "
            f"Status: {status_code} | "
            f"Title: {title[:50]}{'...' if len(title) > 50 else ''} | "
            f"Success: {success}"
        )

        if error:
            log_message += f" | Error: {error}"

        self.logger.info(log_message)

    def fetch_abstract_for_title(self, title: str) -> Optional[str]:
        """
        Fetch abstract for a specific title using Crossref API

        Args:
            title: The paper title to search for

        Returns:
            Abstract text if found, None otherwise
        """
        if not title or title.strip() == "":
            return None

        start_time = time.time()
        response = None

        try:
            # Use basic query format - this works better for abstracts!
            url = f"{self.base_url}?query={title}"

            print(f"🔍 Searching for: {title[:50]}...")
            print(f"🌐 API URL: {url}")

            # Log the API call being made
            self.logger.info(f"Making API request to: {url}")

            # Make API request
            response = requests.get(url, headers=self.headers, timeout=15)
            response_time = time.time() - start_time

            print(f"⏱️  Response time: {response_time:.2f}s | Status: {response.status_code}")

            # Log API response details
            self.log_api_call(url, response_time, response.status_code, title, True)

            response.raise_for_status()

            data = response.json()

            # Log response data summary
            items = data.get('message', {}).get('items', [])
            total_results = data.get('message', {}).get('total-results', 0)
            print(f"📊 API Response: {total_results} total results, {len(items)} items returned")
            self.logger.info(f"API_RESPONSE | Total results: {total_results} | Items returned: {len(items)}")

            if not items:
                print(f"   ❌ No results found")
                self.failed_count += 1
                self.failed_titles.append(title)
                return None

            # Show first few results for debugging
            print(f"🔎 First result details:")
            first_item = items[0]
            item_title = first_item.get('title', ['No title'])[0] if first_item.get('title') else 'No title'
            print(f"   📝 Title: {item_title[:80]}...")
            print(f"   📅 Year: {first_item.get('published-print', {}).get('date-parts', [[None]])[0][0] if first_item.get('published-print') else 'Unknown'}")
            print(f"   📖 Journal: {first_item.get('container-title', ['Unknown'])[0] if first_item.get('container-title') else 'Unknown'}")
            print(f"   📄 Has abstract field: {'abstract' in first_item}")

            if 'abstract' in first_item:
                abstract_preview = str(first_item['abstract'])[:100] if first_item['abstract'] else 'Empty'
                print(f"   📝 Abstract preview: {abstract_preview}...")

            # Find the best matching title
            best_match = self.find_best_title_match(title, items)

            if best_match:
                # Log the matched paper details
                matched_title = best_match.get('title', ['Unknown'])[0] if best_match.get('title') else 'Unknown'
                print(f"✅ Match found: {matched_title[:60]}...")
                self.logger.info(f"MATCH_FOUND | Original: {title[:30]}... | Matched: {matched_title[:30]}...")

                # Try different ways to extract abstract from Crossref API response
                abstract = None

                # Method 1: Direct abstract field
                if 'abstract' in best_match and best_match['abstract']:
                    abstract = best_match['abstract']
                    print(f"📄 Abstract extraction: Direct field method")
                    self.logger.info("ABSTRACT_METHOD | Direct abstract field found")

                # Method 2: Abstract in nested structure (common in Crossref)
                elif 'abstract' in best_match and isinstance(best_match['abstract'], str):
                    abstract = best_match['abstract']
                    print(f"📄 Abstract extraction: String method")
                    self.logger.info("ABSTRACT_METHOD | String abstract found")

                # Method 3: Check if abstract is in XML format or other nested structure
                elif 'abstract' in best_match and best_match['abstract']:
                    if isinstance(best_match['abstract'], dict):
                        # Sometimes abstract is in {'value': 'text'} format
                        abstract = best_match['abstract'].get('value', '')
                        print(f"📄 Abstract extraction: Dict format method")
                        self.logger.info("ABSTRACT_METHOD | Dict format abstract found")
                    elif isinstance(best_match['abstract'], list) and len(best_match['abstract']) > 0:
                        # Sometimes abstract is in array format
                        abstract = best_match['abstract'][0] if isinstance(best_match['abstract'][0], str) else best_match['abstract'][0].get('value', '')
                        print(f"📄 Abstract extraction: Array format method")
                        self.logger.info("ABSTRACT_METHOD | Array format abstract found")

                if abstract and abstract.strip():
                    # Clean up the abstract
                    cleaned_abstract = self.clean_abstract(abstract)
                    if cleaned_abstract:
                        print(f"   ✅ Abstract found ({len(cleaned_abstract)} chars)")
                        print(f"   📝 Abstract snippet: {cleaned_abstract[:100]}...")
                        self.logger.info(f"ABSTRACT_SUCCESS | Length: {len(cleaned_abstract)} chars")
                        self.success_count += 1
                        return cleaned_abstract
                else:
                    print(f"   📄 Abstract field exists but is empty or invalid")
                    self.logger.info("ABSTRACT_EMPTY | Abstract field exists but is empty")
            else:
                print(f"   ❌ No matching title found")

            print(f"   ⚠️ No abstract available")
            self.failed_count += 1
            self.failed_titles.append(title)
            return None

        except requests.exceptions.RequestException as e:
            response_time = time.time() - start_time
            status_code = response.status_code if response else 0
            print(f"   ❌ Request error: {e}")
            print(f"   🌐 Failed URL: {url if 'url' in locals() else 'Unknown'}")
            self.log_api_call(url if 'url' in locals() else 'Unknown', response_time, status_code, title, False, str(e))

            self.failed_count += 1
            self.failed_titles.append(title)
            return None
        except Exception as e:
            response_time = time.time() - start_time
            status_code = response.status_code if response else 0
            print(f"   ❌ Unexpected error: {e}")
            print(f"   🌐 Failed URL: {url if 'url' in locals() else 'Unknown'}")
            self.log_api_call(url if 'url' in locals() else 'Unknown', response_time, status_code, title, False, str(e))

            self.failed_count += 1
            self.failed_titles.append(title)
            return None

    def clean_title(self, title: str) -> str:
        """
        Clean title for better API search
        """
        if not title:
            return ""

        # Remove extra whitespace and special characters that might interfere
        cleaned = re.sub(r'\s+', ' ', title.strip())
        # Remove quotes that might interfere with query
        cleaned = cleaned.replace('"', '').replace("'", "")
        return cleaned

    def find_best_title_match(self, original_title: str, items: list) -> Optional[dict]:
        """
        Find the best matching paper from search results
        """
        original_lower = original_title.lower().strip()

        for item in items:
            if 'title' in item and item['title']:
                api_title = item['title'][0] if isinstance(item['title'], list) else item['title']
                api_title_lower = api_title.lower().strip()

                # Check for exact match or high similarity
                if self.titles_match(original_lower, api_title_lower):
                    return item

        # If no exact match, return the first result (most relevant)
        return items[0] if items else None

    def titles_match(self, title1: str, title2: str) -> bool:
        """
        Check if two titles are similar enough to be considered a match
        """
        # Remove common punctuation and extra spaces
        clean1 = re.sub(r'[^\w\s]', '', title1).strip()
        clean2 = re.sub(r'[^\w\s]', '', title2).strip()

        # Exact match
        if clean1 == clean2:
            return True

        # Check if one title contains the other (accounting for subtitle differences)
        if clean1 in clean2 or clean2 in clean1:
            return True

        # Check similarity by words (at least 80% of words match)
        words1 = set(clean1.split())
        words2 = set(clean2.split())

        if len(words1) == 0 or len(words2) == 0:
            return False

        intersection = words1.intersection(words2)
        similarity = len(intersection) / max(len(words1), len(words2))

        return similarity >= 0.8

    def clean_abstract(self, abstract: str) -> str:
        """
        Clean abstract text
        """
        if not abstract:
            return ""

        # Remove HTML tags
        cleaned = re.sub(r'<[^>]+>', '', abstract)
        # Normalize whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned)
        # Remove extra quotes and trim
        cleaned = cleaned.strip().strip('"').strip("'")

        return cleaned

    def process_csv_file(self, input_file: str, title_column: str = 'title') -> str:
        """
        Process CSV file and add abstracts

        Args:
            input_file: Path to input CSV file
            title_column: Name of the column containing titles

        Returns:
            Path to output CSV file with abstracts
        """
        try:
            # Read the CSV file
            print(f"📖 Reading CSV file: {input_file}")
            df = pd.read_csv(input_file)

            # Check if title column exists
            if title_column not in df.columns:
                available_columns = ', '.join(df.columns)
                raise ValueError(f"Column '{title_column}' not found. Available columns: {available_columns}")

            print(f"📊 Found {len(df)} papers to process")
            print(f"🎯 Title column: '{title_column}'")

            # Initialize abstract column
            df['abstract_fetched'] = None

            print(f"\n🚀 Starting abstract fetching...")
            print("=" * 60)

            # Process each title
            for index, row in df.iterrows():
                title = row[title_column]
                print(f"\n[{index + 1}/{len(df)}] Processing paper...")

                # Fetch abstract
                abstract = self.fetch_abstract_for_title(title)
                df.at[index, 'abstract_fetched'] = abstract

                # Rate limiting - be respectful to the API
                time.sleep(0.5)

                # Progress update every 10 papers
                if (index + 1) % 10 == 0:
                    print(f"\n📈 Progress: {index + 1}/{len(df)} papers processed")
                    print(f"   ✅ Success: {self.success_count}, ❌ Failed: {self.failed_count}")

            # Generate output filename
            input_dir = os.path.dirname(input_file)
            input_name = os.path.splitext(os.path.basename(input_file))[0]
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(input_dir, f"{input_name}_with_abstracts_{timestamp}.csv")

            # Save the updated CSV
            df.to_csv(output_file, index=False)

            # Print summary
            print("\n" + "=" * 60)
            print("🎉 Abstract fetching completed!")
            print(f"📊 Summary:")
            print(f"   📝 Total papers: {len(df)}")
            print(f"   ✅ Abstracts found: {self.success_count}")
            print(f"   ❌ Abstracts not found: {self.failed_count}")
            print(f"   📈 Success rate: {(self.success_count/len(df)*100):.1f}%")
            print(f"💾 Output saved to: {output_file}")

            # Save failed titles for reference
            # if self.failed_titles:
            #     failed_file = os.path.join(input_dir, f"failed_abstracts_{timestamp}.txt")
            #     with open(failed_file, 'w') as f:
            #         f.write("Titles for which abstracts could not be found:\n\n")
            #         for i, title in enumerate(self.failed_titles, 1):
            #             f.write(f"{i}. {title}\n")
            #     print(f"📄 Failed titles saved to: {failed_file}")

            return output_file

        except FileNotFoundError:
            raise FileNotFoundError(f"Input file not found: {input_file}")
        except Exception as e:
            raise Exception(f"Error processing CSV file: {str(e)}")


def get_user_input():
    """
    Get input file and column name from user
    """
    print("🔬 Title to Abstract Fetcher")
    print("=" * 50)

    # Get input file path
    while True:
        input_file = input("📁 Enter path to CSV file: ").strip()
        if input_file and os.path.exists(input_file):
            break
        print("❌ File not found. Please enter a valid file path.")

    # Get title column name
    try:
        df_sample = pd.read_csv(input_file, nrows=1)
        available_columns = list(df_sample.columns)
        print(f"\n📋 Available columns: {', '.join(available_columns)}")

        title_column = input(f"📝 Enter title column name (default: 'title'): ").strip()
        if not title_column:
            title_column = 'title'

        if title_column not in available_columns:
            print(f"⚠️ Column '{title_column}' not found. Using 'title' as default.")
            title_column = 'title'

    except Exception as e:
        print(f"⚠️ Could not read CSV columns: {e}")
        title_column = 'title'

    return input_file, title_column


def main():
    """
    Main function
    """
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(description='Fetch abstracts for paper titles from CSV')
        parser.add_argument('--input', '-i', help='Input CSV file path')
        parser.add_argument('--column', '-c', default='title', help='Title column name (default: title)')

        args = parser.parse_args()

        if args.input:
            # Command line mode
            input_file = args.input
            title_column = args.column

            if not os.path.exists(input_file):
                print(f"❌ Error: File not found: {input_file}")
                return
        else:
            # Interactive mode
            input_file, title_column = get_user_input()

        # Create fetcher and process the file
        fetcher = TitleToAbstractFetcher()
        output_file = fetcher.process_csv_file(input_file, title_column)

        print(f"\n🎉 Process completed successfully!")
        print(f"📄 Output file: {output_file}")

    except KeyboardInterrupt:
        print(f"\n\n⚠️ Process interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


if __name__ == "__main__":
    main()
