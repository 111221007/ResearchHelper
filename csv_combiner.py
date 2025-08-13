#!/usr/bin/env python3
"""
CSV Combiner and Deduplicator
Combines multiple CSV files and removes duplicates based on title similarity
"""

import pandas as pd
import os
import re
from datetime import datetime
import argparse
import logging

class CSVCombiner:
    def __init__(self):
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

    def title_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between two titles"""
        if not title1 or not title2:
            return 0.0
        
        # Normalize titles
        title1 = re.sub(r'[^\w\s]', ' ', str(title1).lower()).strip()
        title2 = re.sub(r'[^\w\s]', ' ', str(title2).lower()).strip()
        
        words1 = set(title1.split())
        words2 = set(title2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0

    def find_duplicates(self, df: pd.DataFrame, similarity_threshold: float = 0.85) -> list:
        """Find duplicate papers based on title similarity"""
        duplicates = []
        titles = df['title'].fillna('').tolist()
        
        for i in range(len(titles)):
            for j in range(i + 1, len(titles)):
                if self.title_similarity(titles[i], titles[j]) >= similarity_threshold:
                    duplicates.append(j)  # Mark the later one as duplicate
        
        return list(set(duplicates))

    def combine_csvs(self, input_dir: str, output_path: str) -> pd.DataFrame:
        """Combine all CSV files in the directory"""
        
        # Find all CSV files
        csv_files = [f for f in os.listdir(input_dir) if f.endswith('.csv')]
        self.logger.info(f"Found {len(csv_files)} CSV files to combine")
        
        combined_df = pd.DataFrame()
        
        for csv_file in csv_files:
            file_path = os.path.join(input_dir, csv_file)
            self.logger.info(f"Processing: {csv_file}")
            
            try:
                df = pd.read_csv(file_path)
                self.logger.info(f"  - Loaded {len(df)} rows")
                
                # Ensure required columns exist
                required_columns = ['paper_id', 'title', 'abstract', 'authors', 'journal', 
                                  'year', 'volume', 'issue', 'pages', 'publisher', 'doi', 'url', 'type']
                
                for col in required_columns:
                    if col not in df.columns:
                        df[col] = ''
                
                # Select only the required columns
                df = df[required_columns]
                
                # Combine with main dataframe
                combined_df = pd.concat([combined_df, df], ignore_index=True)
                
            except Exception as e:
                self.logger.error(f"Error processing {csv_file}: {e}")
        
        self.logger.info(f"Combined total: {len(combined_df)} papers")
        
        # Remove duplicates
        self.logger.info("Finding duplicates...")
        duplicate_indices = self.find_duplicates(combined_df)
        self.logger.info(f"Found {len(duplicate_indices)} duplicates")
        
        # Remove duplicates
        deduplicated_df = combined_df.drop(index=duplicate_indices).reset_index(drop=True)
        self.logger.info(f"After deduplication: {len(deduplicated_df)} papers")
        
        # Reassign paper IDs
        for idx in range(len(deduplicated_df)):
            deduplicated_df.at[idx, 'paper_id'] = f"paper_{idx+1:03d}"
        
        # Save intermediate result
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        intermediate_path = output_path.replace('.csv', f'_deduplicated_{timestamp}.csv')
        deduplicated_df.to_csv(intermediate_path, index=False)
        self.logger.info(f"Deduplicated file saved: {intermediate_path}")
        
        return deduplicated_df

def main():
    parser = argparse.ArgumentParser(description='Combine and deduplicate CSV files')
    parser.add_argument('--input-dir', default='/Users/reddy/Downloads/UDPATED_11_AUG_8AM', 
                       help='Directory containing CSV files to combine')
    parser.add_argument('--output', default='/Users/reddy/2025/ResearchHelper/results/combined_papers_deduplicated.csv',
                       help='Output CSV file path')
    
    args = parser.parse_args()
    
    combiner = CSVCombiner()
    result_df = combiner.combine_csvs(args.input_dir, args.output)
    
    # Save final result
    result_df.to_csv(args.output, index=False)
    print(f"\nFinal combined and deduplicated file saved: {args.output}")
    print(f"Total papers: {len(result_df)}")

if __name__ == "__main__":
    main()
