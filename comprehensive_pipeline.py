#!/usr/bin/env python3
"""
Comprehensive Research Paper Pipeline Controller
Orchestrates the complete pipeline: multi-keyword fetch -> deduplicate -> abstract enhancement -> PDF download -> categorization
"""

import pandas as pd
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional
import logging
import json

# Import our custom modules
from multi_keyword_fetcher import MultiKeywordPaperFetcher
from abstract_digger import AbstractDigger
from enhanced_pdf_downloader import EnhancedPDFDownloader
from category_keyword_extractor import CategoryKeywordExtractor

class ComprehensivePaperPipeline:
    def __init__(self, output_dir: str = "/Users/reddy/2025/ResearchHelper/results"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        # Setup logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.fetcher = MultiKeywordPaperFetcher(output_dir)
        self.abstract_digger = AbstractDigger(output_dir)
        self.pdf_downloader = EnhancedPDFDownloader(output_dir)
        self.category_extractor = CategoryKeywordExtractor(output_dir)

        # Pipeline statistics
        self.stats = {
            'start_time': None,
            'end_time': None,
            'total_configurations': 0,
            'papers_fetched': 0,
            'papers_after_deduplication': 0,
            'abstracts_enhanced': 0,
            'pdfs_downloaded': 0,
            'papers_categorized': 0,
            'final_csv_path': ''
        }

    def run_complete_pipeline(self, keyword_configs: List[Dict],
                            enable_pdf_download: bool = True,
                            enable_abstract_enhancement: bool = True,
                            enable_categorization: bool = True) -> Dict:
        """
        Run the complete research paper pipeline

        Args:
            keyword_configs: List of keyword configurations
            enable_pdf_download: Whether to download PDFs
            enable_abstract_enhancement: Whether to enhance abstracts
            enable_categorization: Whether to categorize papers

        Returns:
            Dictionary with pipeline results and statistics
        """

        self.stats['start_time'] = datetime.now()
        self.stats['total_configurations'] = len(keyword_configs)

        self.logger.info("🚀 Starting Comprehensive Research Paper Pipeline")
        self.logger.info(f"Configurations: {len(keyword_configs)}")
        self.logger.info(f"PDF Download: {'Enabled' if enable_pdf_download else 'Disabled'}")
        self.logger.info(f"Abstract Enhancement: {'Enabled' if enable_abstract_enhancement else 'Disabled'}")
        self.logger.info(f"Categorization: {'Enabled' if enable_categorization else 'Disabled'}")

        try:
            # Step 1: Multi-keyword paper fetching and deduplication
            self.logger.info("\n📋 STEP 1: Multi-keyword paper fetching and deduplication")
            combined_csv_path = self.fetcher.fetch_multi_keyword_papers(keyword_configs)

            # Read to get counts
            df = pd.read_csv(combined_csv_path)
            self.stats['papers_fetched'] = len(df)
            self.stats['papers_after_deduplication'] = len(df)

            current_csv = combined_csv_path

            # Step 2: Abstract enhancement (if enabled)
            if enable_abstract_enhancement:
                self.logger.info("\n🔍 STEP 2: Abstract enhancement")
                enhanced_df = self.abstract_digger.process_papers(current_csv)

                # Save enhanced CSV
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                enhanced_csv_name = f"papers_with_abstracts_{timestamp}.csv"
                enhanced_csv_path = os.path.join(self.output_dir, enhanced_csv_name)
                enhanced_df.to_csv(enhanced_csv_path, index=False)

                current_csv = enhanced_csv_path
                self.stats['abstracts_enhanced'] = len(enhanced_df[enhanced_df['abstract_source'] != ''])

                self.logger.info(f"Abstract enhancement completed. Enhanced CSV: {enhanced_csv_path}")

            # Step 3: PDF download (if enabled)
            if enable_pdf_download:
                self.logger.info("\n📥 STEP 3: PDF download")
                pdf_enhanced_csv = self.pdf_downloader.download_papers_batch(current_csv, max_workers=3)
                current_csv = pdf_enhanced_csv

                # Count successful downloads
                df_with_pdfs = pd.read_csv(current_csv)
                self.stats['pdfs_downloaded'] = len(df_with_pdfs[df_with_pdfs['pdf_downloaded'] == True])

                self.logger.info(f"PDF download completed. Enhanced CSV: {pdf_enhanced_csv}")

            # Step 4: Categorization and keyword extraction (if enabled)
            if enable_categorization:
                self.logger.info("\n🏷️ STEP 4: Categorization and keyword extraction")
                final_csv_path = self.category_extractor.process_papers_csv(current_csv)
                current_csv = final_csv_path

                # Count categorized papers
                df_categorized = pd.read_csv(current_csv)
                self.stats['papers_categorized'] = len(df_categorized[df_categorized['original_category'] != ''])

                self.logger.info(f"Categorization completed. Final CSV: {final_csv_path}")

            # Final step: Ensure all required columns and clean up
            self.logger.info("\n✨ STEP 5: Final processing and cleanup")
            final_csv_path = self._finalize_csv(current_csv)

            self.stats['final_csv_path'] = final_csv_path
            self.stats['end_time'] = datetime.now()

            # Print comprehensive summary
            self._print_pipeline_summary()

            return {
                'success': True,
                'final_csv_path': final_csv_path,
                'statistics': self.stats,
                'message': 'Pipeline completed successfully'
            }

        except Exception as e:
            self.logger.error(f"Pipeline failed: {e}")
            self.stats['end_time'] = datetime.now()
            return {
                'success': False,
                'error': str(e),
                'statistics': self.stats,
                'message': f'Pipeline failed: {e}'
            }

    def _finalize_csv(self, csv_path: str) -> str:
        """Final processing of the CSV to ensure all columns are present and clean"""
        df = pd.read_csv(csv_path)

        # Ensure all required columns exist
        required_columns = [
            'paper_id', 'title', 'abstract', 'authors', 'journal', 'year', 'volume',
            'issue', 'pages', 'publisher', 'doi', 'url', 'type', 'abstract_source',
            'abstract_confidence', 'original_category', 'original_keywords',
            'contributions', 'limitations'
        ]

        for col in required_columns:
            if col not in df.columns:
                df[col] = ''

        # Clean up data
        df = df.fillna('')

        # Reorder columns
        df = df[required_columns]

        # Sort by paper_id
        df = df.sort_values('paper_id')

        # Save final CSV
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_filename = f"final_research_papers_complete_{timestamp}.csv"
        final_path = os.path.join(self.output_dir, final_filename)
        df.to_csv(final_path, index=False)

        self.logger.info(f"Final CSV saved: {final_path}")
        return final_path

    def _print_pipeline_summary(self):
        """Print comprehensive pipeline summary"""
        duration = self.stats['end_time'] - self.stats['start_time']

        print(f"\n🎉 COMPREHENSIVE PIPELINE SUMMARY")
        print(f"=" * 50)
        print(f"⏱️  Total Duration: {duration}")
        print(f"🔧 Configurations Processed: {self.stats['total_configurations']}")
        print(f"📄 Papers Fetched: {self.stats['papers_fetched']}")
        print(f"🔄 Papers After Deduplication: {self.stats['papers_after_deduplication']}")
        print(f"📝 Abstracts Enhanced: {self.stats['abstracts_enhanced']}")
        print(f"📥 PDFs Downloaded: {self.stats['pdfs_downloaded']}")
        print(f"🏷️  Papers Categorized: {self.stats['papers_categorized']}")
        print(f"📊 Final CSV: {self.stats['final_csv_path']}")

        # Calculate success rates
        if self.stats['papers_after_deduplication'] > 0:
            abstract_rate = (self.stats['abstracts_enhanced'] / self.stats['papers_after_deduplication']) * 100
            pdf_rate = (self.stats['pdfs_downloaded'] / self.stats['papers_after_deduplication']) * 100
            category_rate = (self.stats['papers_categorized'] / self.stats['papers_after_deduplication']) * 100

            print(f"\n📈 SUCCESS RATES:")
            print(f"Abstract Enhancement: {abstract_rate:.1f}%")
            print(f"PDF Download: {pdf_rate:.1f}%")
            print(f"Categorization: {category_rate:.1f}%")

        print(f"=" * 50)


def main():
    """Main function for command line usage"""
    if len(sys.argv) < 2:
        print("Usage: python comprehensive_pipeline.py <config_file.json>")
        print("\nExample config file format:")
        print(json.dumps([
            {
                "primary_keyword": "serverless computing",
                "secondary_keyword": "performance",
                "from_year": 2020,
                "to_year": 2025,
                "max_results": 30
            },
            {
                "primary_keyword": "serverless",
                "secondary_keyword": "security",
                "from_year": 2020,
                "to_year": 2025,
                "max_results": 30
            }
        ], indent=2))
        sys.exit(1)

    config_file = sys.argv[1]
    if not os.path.exists(config_file):
        print(f"Error: Configuration file '{config_file}' not found!")
        sys.exit(1)

    # Load configuration
    try:
        with open(config_file, 'r') as f:
            keyword_configs = json.load(f)
    except Exception as e:
        print(f"Error loading configuration file: {e}")
        sys.exit(1)

    # Run pipeline
    pipeline = ComprehensivePaperPipeline()
    result = pipeline.run_complete_pipeline(
        keyword_configs=keyword_configs,
        enable_pdf_download=True,
        enable_abstract_enhancement=True,
        enable_categorization=True
    )

    if result['success']:
        print(f"\n✅ Pipeline completed successfully!")
        print(f"Final results: {result['final_csv_path']}")
    else:
        print(f"\n❌ Pipeline failed: {result['message']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
