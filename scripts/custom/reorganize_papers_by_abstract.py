import pandas as pd
import os
from datetime import datetime

def reorganize_papers_by_abstract():
    """
    Reorganize CSV to move papers without abstracts to the end and update paper IDs
    """

    # Input file path
    input_path = "/Users/reddy/2025/ResearchHelper/results/combined_papers_deduplicated_with_abstracts_20250811_103658.csv"

    try:
        # Read the CSV file
        df = pd.read_csv(input_path)
        print(f"📊 Loaded {len(df)} papers from the file")

        # Check if abstract column exists
        if 'abstract' not in df.columns:
            print("❌ Error: 'abstract' column not found in the CSV file")
            return

        # Analyze current abstract status
        print("\n🔍 Analyzing abstract availability...")

        # Define what constitutes "no abstract"
        no_abstract_conditions = (
            df['abstract'].isna() |
            (df['abstract'] == '') |
            (df['abstract'] == 'Not found') |
            (df['abstract'].str.strip() == '')
        )

        papers_with_abstracts = df[~no_abstract_conditions]
        papers_without_abstracts = df[no_abstract_conditions]

        print(f"   Papers with abstracts: {len(papers_with_abstracts)}")
        print(f"   Papers without abstracts: {len(papers_without_abstracts)}")

        if len(papers_without_abstracts) == 0:
            print("✅ All papers already have abstracts! No reorganization needed.")
            return

        # Show breakdown of papers without abstracts
        if len(papers_without_abstracts) > 0:
            print("\n📋 Breakdown of papers without abstracts:")
            no_abstract_breakdown = papers_without_abstracts['abstract'].value_counts(dropna=False)
            for value, count in no_abstract_breakdown.items():
                print(f"   '{value}': {count} papers")

        # Reorganize: papers with abstracts first, then papers without abstracts
        print("\n🔄 Reorganizing papers...")
        reorganized_df = pd.concat([papers_with_abstracts, papers_without_abstracts], ignore_index=True)

        # Update paper IDs sequentially
        reorganized_df['paper_id'] = [f"paper_{i+1:03d}" for i in range(len(reorganized_df))]

        # Create output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"combined_papers_reorganized_{timestamp}.csv"
        output_dir = os.path.dirname(input_path)
        output_path = os.path.join(output_dir, output_filename)

        # Save reorganized file
        reorganized_df.to_csv(output_path, index=False)

        print(f"\n✅ Successfully reorganized papers!")
        print(f"📁 Saved to: {output_path}")

        # Summary statistics
        print("\n📈 REORGANIZATION SUMMARY:")
        print(f"   Total papers: {len(reorganized_df)}")
        print(f"   Papers with abstracts (positions 1-{len(papers_with_abstracts)}): {len(papers_with_abstracts)}")
        print(f"   Papers without abstracts (positions {len(papers_with_abstracts)+1}-{len(reorganized_df)}): {len(papers_without_abstracts)}")
        print(f"   Percentage with abstracts: {(len(papers_with_abstracts)/len(reorganized_df)*100):.1f}%")

        # Show sample of reorganized data
        print("\n📋 Sample of reorganized data:")
        print("First 3 papers (with abstracts):")
        for i in range(min(3, len(papers_with_abstracts))):
            row = reorganized_df.iloc[i]
            abstract_preview = row['abstract'][:100] + "..." if len(str(row['abstract'])) > 100 else row['abstract']
            print(f"   {row['paper_id']}: {row['title'][:50]}...")
            print(f"   Abstract: {abstract_preview}")
            print()

        if len(papers_without_abstracts) > 0:
            print("Last 3 papers (without abstracts):")
            start_idx = len(papers_with_abstracts)
            for i in range(min(3, len(papers_without_abstracts))):
                row = reorganized_df.iloc[start_idx + i]
                print(f"   {row['paper_id']}: {row['title'][:50]}...")
                print(f"   Abstract: {row['abstract']}")
                print()

        # Verify the reorganization
        print("🔍 Verification:")

        # Check if all papers with abstracts are at the beginning
        verification_df = reorganized_df.copy()
        verification_no_abstract = (
            verification_df['abstract'].isna() |
            (verification_df['abstract'] == '') |
            (verification_df['abstract'] == 'Not found') |
            (verification_df['abstract'].str.strip() == '')
        )

        first_no_abstract_index = verification_df[verification_no_abstract].index.min() if verification_no_abstract.any() else len(verification_df)
        papers_with_abstracts_at_start = verification_df[:first_no_abstract_index]
        papers_without_abstracts_at_end = verification_df[first_no_abstract_index:]

        has_abstracts_in_start = ~(
            papers_with_abstracts_at_start['abstract'].isna() |
            (papers_with_abstracts_at_start['abstract'] == '') |
            (papers_with_abstracts_at_start['abstract'] == 'Not found') |
            (papers_with_abstracts_at_start['abstract'].str.strip() == '')
        )

        if has_abstracts_in_start.all():
            print("   ✅ All papers at the beginning have abstracts")
        else:
            print("   ❌ Some papers at the beginning don't have abstracts")

        if len(papers_without_abstracts_at_end) == len(papers_without_abstracts):
            print("   ✅ All papers without abstracts are at the end")
        else:
            print("   ❌ Not all papers without abstracts are at the end")

        # Show abstract source breakdown for papers with abstracts
        if 'abstract_source' in reorganized_df.columns:
            papers_with_valid_abstracts = reorganized_df[~verification_no_abstract]
            if len(papers_with_valid_abstracts) > 0:
                print(f"\n📊 Abstract sources for {len(papers_with_valid_abstracts)} papers with abstracts:")
                source_counts = papers_with_valid_abstracts['abstract_source'].value_counts()
                for source, count in source_counts.items():
                    print(f"   {source}: {count} abstracts")

        return output_path

    except FileNotFoundError:
        print(f"❌ Error: Could not find file {input_path}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    reorganize_papers_by_abstract()
