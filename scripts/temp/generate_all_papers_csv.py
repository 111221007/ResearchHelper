#!/usr/bin/env python3
"""
Script to generate a comprehensive CSV file with all papers from all paper lists.
This script handles importing from all paper_list_X.py files and creates a unified CSV.
"""

import sys
import os
import pandas as pd
import csv

# Ensure we can import from current directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def load_all_papers():
    """Load papers from all paper list files and normalize them"""
    all_papers = []

    # Load from paper_list_1
    try:
        from paper_list_1 import papers as papers1
        for paper in papers1:
            normalized = {
                "unified_id": len(all_papers) + 1,
                "original_id": paper.get('id', ''),
                "title": paper.get('title', ''),
                "authors": paper.get('authors', ''),
                "year": paper.get('year', ''),
                "venue": paper.get('venue', ''),
                "category": paper.get('category', ''),
                "keywords": paper.get('keywords', ''),
                "pdf_link": paper.get('pdf_link', ''),
                "doi": paper.get('doi', ''),
                "source_list": "paper_list_1"
            }
            all_papers.append(normalized)
        print(f"Loaded {len(papers1)} papers from paper_list_1")
    except Exception as e:
        print(f"Could not load paper_list_1: {e}")

    # Load from paper_list_2
    try:
        from paper_list_2 import papers as papers2
        for paper in papers2:
            normalized = {
                "unified_id": len(all_papers) + 1,
                "original_id": paper.get('id', ''),
                "title": paper.get('title', ''),
                "authors": paper.get('authors', ''),
                "year": paper.get('year', ''),
                "venue": paper.get('venue', ''),
                "category": paper.get('category', ''),
                "keywords": paper.get('keywords', ''),
                "pdf_link": paper.get('pdf_link', paper.get('url', '')),
                "doi": paper.get('doi', ''),
                "source_list": "paper_list_2"
            }
            all_papers.append(normalized)
        print(f"Loaded {len(papers2)} papers from paper_list_2")
    except Exception as e:
        print(f"Could not load paper_list_2: {e}")

    # Load from paper_list_3
    try:
        from paper_list_3 import papers as papers3
        for paper in papers3:
            normalized = {
                "unified_id": len(all_papers) + 1,
                "original_id": paper.get('id', ''),
                "title": paper.get('title', ''),
                "authors": paper.get('authors', ''),
                "year": paper.get('year', ''),
                "venue": paper.get('venue', ''),
                "category": paper.get('category', ''),
                "keywords": paper.get('keywords', ''),
                "pdf_link": paper.get('pdf_link', ''),
                "doi": paper.get('doi', ''),
                "source_list": "paper_list_3"
            }
            all_papers.append(normalized)
        print(f"Loaded {len(papers3)} papers from paper_list_3")
    except Exception as e:
        print(f"Could not load paper_list_3: {e}")

    # Load from paper_list_4
    try:
        from paper_list_4 import papers as papers4
        for paper in papers4:
            normalized = {
                "unified_id": len(all_papers) + 1,
                "original_id": paper.get('id', ''),
                "title": paper.get('title', ''),
                "authors": paper.get('authors', ''),
                "year": paper.get('year', ''),
                "venue": paper.get('venue', ''),
                "category": paper.get('category', ''),
                "keywords": paper.get('keywords', ''),
                "pdf_link": paper.get('pdf_link', ''),
                "doi": paper.get('doi', ''),
                "source_list": "paper_list_4"
            }
            all_papers.append(normalized)
        print(f"Loaded {len(papers4)} papers from paper_list_4")
    except Exception as e:
        # Try alternative import if papers4 doesn't have the expected structure
        try:
            from paper_list_4 import extended_papers as papers4
            for paper in papers4:
                normalized = {
                    "unified_id": len(all_papers) + 1,
                    "original_id": paper.get('id', ''),
                    "title": paper.get('title', ''),
                    "authors": paper.get('authors', ''),
                    "year": paper.get('year', ''),
                    "venue": paper.get('venue', ''),
                    "category": paper.get('category', ''),
                    "keywords": paper.get('keywords', ''),
                    "pdf_link": paper.get('pdf_link', ''),
                    "doi": paper.get('doi', ''),
                    "source_list": "paper_list_4"
                }
                all_papers.append(normalized)
            print(f"Loaded {len(papers4)} papers from paper_list_4 (extended_papers)")
        except Exception as e2:
            print(f"Could not load paper_list_4: {e2}")

    print(f"Total papers loaded: {len(all_papers)}")
    return all_papers

def create_metrics_table(papers, output_dir="results"):
    """Create a DataFrame with metrics coverage for each paper"""
    # Define metric categories and their keywords
    metric_keywords = {
        "Latency": ["latency", "cold start", "response time", "tail latency", "startup time", "delay"],
        "Reliability & QoS": ["reliability", "qos", "quality of service", "sla", "slo", "fairness"],
        "Security & Privacy": ["security", "privacy", "attack", "vulnerability", "authentication"],
        "Cost": ["cost", "pricing", "revenue", "billing", "economic"],
        "Energy Consumption": ["energy", "power", "consumption", "carbon", "footprint", "green"],
        "Resource Management": ["resource", "scheduling", "allocation", "provisioning", "autoscaling"],
        "Benchmarking & Evaluation": ["benchmark", "evaluation", "performance", "test", "comparison"]
    }

    # Create DataFrame
    df = pd.DataFrame(papers)

    # Add binary columns for each metric category
    for metric, keywords in metric_keywords.items():
        df[metric] = df.apply(
            lambda row: any(
                keyword.lower() in str(row.get('title', '')).lower() or
                keyword.lower() in str(row.get('category', '')).lower() or
                keyword.lower() in str(row.get('keywords', '')).lower()
                for keyword in keywords
            ),
            axis=1
        )
        # Convert boolean to Yes/No for better CSV readability
        df[metric] = df[metric].map({True: "Yes", False: "No"})

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Export to CSV
    csv_path = os.path.join(output_dir, "all_papers.csv")
    df.to_csv(csv_path, index=False)
    print(f"Saved all papers with metrics to: {csv_path}")

    return df

def generate_metrics_summary(df, output_dir="results"):
    """Generate summary of metrics coverage"""
    # Convert Yes/No back to True/False for counting
    metric_columns = ["Latency", "Reliability & QoS", "Security & Privacy", "Cost",
                     "Energy Consumption", "Resource Management", "Benchmarking & Evaluation"]

    for col in metric_columns:
        df[col] = df[col].map({"Yes": True, "No": False})

    # Count papers by metric
    metric_counts = {metric: df[metric].sum() for metric in metric_columns}

    # Create summary DataFrame
    summary_df = pd.DataFrame({
        'Metric': list(metric_counts.keys()),
        'Paper Count': list(metric_counts.values()),
        'Percentage': [f"{(count / len(df) * 100):.1f}%" for count in metric_counts.values()]
    })

    # Export summary to CSV
    summary_path = os.path.join(output_dir, "metrics_summary.csv")
    summary_df.to_csv(summary_path, index=False)
    print(f"Saved metrics summary to: {summary_path}")

    # Print summary
    print("\nMetrics Coverage Summary:")
    print(f"Total papers: {len(df)}")
    for metric, count in metric_counts.items():
        print(f"  {metric}: {count} papers ({(count / len(df) * 100):.1f}%)")

def main():
    # Load all papers from all sources
    papers = load_all_papers()

    # Create metrics table and export to CSV
    df = create_metrics_table(papers)

    # Generate and export metrics summary
    generate_metrics_summary(df)

if __name__ == "__main__":
    main()
