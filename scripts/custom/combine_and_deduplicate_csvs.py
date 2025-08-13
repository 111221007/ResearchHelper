import pandas as pd
import os
from datetime import datetime
import glob

def combine_csv_files_and_remove_duplicates():
    """
    Combine all CSV files from the Downloads directory and remove duplicates
    """

    # Source directory
    source_dir = "/Users/reddy/Downloads/UDPATED_11_AUG_8AM"

    # Get all CSV files
    csv_files = glob.glob(os.path.join(source_dir, "*.csv"))

    print(f"Found {len(csv_files)} CSV files to combine:")
    for file in csv_files:
        print(f"  - {os.path.basename(file)}")

    # List to store all dataframes
    all_dataframes = []

    # Read each CSV file
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file)
            df['source_file'] = os.path.basename(csv_file)  # Track source file
            all_dataframes.append(df)
            print(f"✅ Loaded {len(df)} papers from {os.path.basename(csv_file)}")
        except Exception as e:
            print(f"❌ Error reading {os.path.basename(csv_file)}: {str(e)}")

    if not all_dataframes:
        print("❌ No valid CSV files found!")
        return

    # Combine all dataframes
    combined_df = pd.concat(all_dataframes, ignore_index=True)
    print(f"\n📊 Total papers before deduplication: {len(combined_df)}")

    # Show source file breakdown
    source_breakdown = combined_df['source_file'].value_counts()
    print(f"\n📁 Papers per source file:")
    for source, count in source_breakdown.items():
        print(f"   {source}: {count} papers")

    # Remove duplicates based on multiple criteria
    print(f"\n🔍 Checking for duplicates...")

    # Method 1: Remove exact duplicates based on title
    initial_count = len(combined_df)
    combined_df_dedup1 = combined_df.drop_duplicates(subset=['title'], keep='first')
    title_duplicates = initial_count - len(combined_df_dedup1)
    print(f"   Removed {title_duplicates} exact title duplicates")

    # Method 2: Remove duplicates based on DOI (if available)
    if 'doi' in combined_df_dedup1.columns:
        # Only check DOI duplicates where DOI is not empty
        doi_mask = combined_df_dedup1['doi'].notna() & (combined_df_dedup1['doi'] != '')
        doi_count_before = len(combined_df_dedup1[doi_mask])
        combined_df_dedup2 = combined_df_dedup1.drop_duplicates(subset=['doi'], keep='first')
        doi_count_after = len(combined_df_dedup2[combined_df_dedup2['doi'].notna() & (combined_df_dedup2['doi'] != '')])
        doi_duplicates = doi_count_before - doi_count_after
        print(f"   Removed {doi_duplicates} DOI-based duplicates")
    else:
        combined_df_dedup2 = combined_df_dedup1
        doi_duplicates = 0

    # Method 3: Remove similar titles (fuzzy matching)
    def similar_titles(df, threshold=0.8):
        """Find similar titles using simple word overlap"""
        duplicates = []
        titles = df['title'].str.lower().str.split()

        for i in range(len(titles)):
            if i in duplicates:
                continue
            for j in range(i + 1, len(titles)):
                if j in duplicates:
                    continue

                title1_words = set(titles.iloc[i]) if isinstance(titles.iloc[i], list) else set()
                title2_words = set(titles.iloc[j]) if isinstance(titles.iloc[j], list) else set()

                if len(title1_words) > 0 and len(title2_words) > 0:
                    intersection = title1_words.intersection(title2_words)
                    union = title1_words.union(title2_words)
                    jaccard_similarity = len(intersection) / len(union)

                    if jaccard_similarity > threshold:
                        duplicates.append(j)

        return duplicates

    print(f"   Checking for similar titles...")
    similar_indices = similar_titles(combined_df_dedup2)
    combined_df_final = combined_df_dedup2.drop(combined_df_dedup2.index[similar_indices])
    similar_duplicates = len(similar_indices)
    print(f"   Removed {similar_duplicates} similar title duplicates")

    # Reset paper_id to be sequential
    combined_df_final = combined_df_final.reset_index(drop=True)
    combined_df_final['paper_id'] = [f"paper_{i+1:03d}" for i in range(len(combined_df_final))]

    # Remove the source_file column from final output
    if 'source_file' in combined_df_final.columns:
        source_tracking = combined_df_final[['paper_id', 'title', 'source_file']].copy()
        combined_df_final = combined_df_final.drop('source_file', axis=1)

    # Final statistics
    print(f"\n📈 DEDUPLICATION SUMMARY:")
    print(f"   Original papers: {initial_count}")
    print(f"   Title duplicates removed: {title_duplicates}")
    print(f"   DOI duplicates removed: {doi_duplicates}")
    print(f"   Similar title duplicates removed: {similar_duplicates}")
    print(f"   Final unique papers: {len(combined_df_final)}")
    print(f"   Total duplicates removed: {initial_count - len(combined_df_final)}")
    print(f"   Deduplication rate: {((initial_count - len(combined_df_final))/initial_count*100):.1f}%")

    # Save the combined and deduplicated file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"combined_papers_deduplicated_{timestamp}.csv"
    output_path = os.path.join(source_dir, output_filename)

    combined_df_final.to_csv(output_path, index=False)
    print(f"\n💾 Saved combined file: {output_path}")

    # Save source tracking file
    tracking_filename = f"source_tracking_{timestamp}.csv"
    tracking_path = os.path.join(source_dir, tracking_filename)
    source_tracking.to_csv(tracking_path, index=False)
    print(f"💾 Saved source tracking: {tracking_path}")

    # Show sample of final data
    print(f"\n📋 Sample of final combined data:")
    print(f"Columns: {list(combined_df_final.columns)}")

    if len(combined_df_final) > 0:
        print(f"\nFirst 3 papers:")
        for i in range(min(3, len(combined_df_final))):
            row = combined_df_final.iloc[i]
            print(f"{i+1}. ID: {row['paper_id']}")
            print(f"   Title: {row['title'][:80]}...")
            print(f"   Year: {row['year']}")
            print(f"   Journal: {row['journal'][:50]}...")
            print()

    # Show year distribution
    if 'year' in combined_df_final.columns:
        year_dist = combined_df_final['year'].value_counts().sort_index(ascending=False)
        print(f"📅 Year distribution (top 10):")
        for year, count in year_dist.head(10).items():
            print(f"   {year}: {count} papers")

    # Show journal distribution
    if 'journal' in combined_df_final.columns:
        journal_dist = combined_df_final['journal'].value_counts()
        print(f"\n📚 Top 10 journals/venues:")
        for journal, count in journal_dist.head(10).items():
            print(f"   {journal[:60]}...: {count} papers")

    print(f"\n🎉 Successfully combined and deduplicated all CSV files!")
    return output_path

if __name__ == "__main__":
    combine_csv_files_and_remove_duplicates()
