#!/usr/bin/env python3
"""
This script combines all papers from all paper list files into a single consolidated CSV file.
"""

import pandas as pd
import os
import sys
import importlib.util

def import_module_from_path(module_name, file_path):
    """Import a module from a file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def load_papers(scripts_dir):
    """Load all papers from all paper list files."""
    all_papers = []

    # Load paper_list_1
    try:
        paper_list_1_path = os.path.join(scripts_dir, "paper_list_1.py")
        paper_list_1 = import_module_from_path("paper_list_1", paper_list_1_path)
        papers1 = getattr(paper_list_1, "papers", [])
        print(f"Loaded {len(papers1)} papers from paper_list_1.py")

        for paper in papers1:
            paper["source"] = "paper_list_1"
            all_papers.append(paper)
    except Exception as e:
        print(f"Error loading paper_list_1.py: {e}")

    # Load paper_list_2
    try:
        paper_list_2_path = os.path.join(scripts_dir, "paper_list_2.py")
        paper_list_2 = import_module_from_path("paper_list_2", paper_list_2_path)
        papers2 = getattr(paper_list_2, "papers", [])
        print(f"Loaded {len(papers2)} papers from paper_list_2.py")

        for paper in papers2:
            paper["source"] = "paper_list_2"
            all_papers.append(paper)
    except Exception as e:
        print(f"Error loading paper_list_2.py: {e}")

    # Load paper_list_3
    try:
        paper_list_3_path = os.path.join(scripts_dir, "paper_list_3.py")
        paper_list_3 = import_module_from_path("paper_list_3", paper_list_3_path)
        papers3 = getattr(paper_list_3, "papers", [])
        print(f"Loaded {len(papers3)} papers from paper_list_3.py")

        for paper in papers3:
            paper["source"] = "paper_list_3"
            all_papers.append(paper)
    except Exception as e:
        print(f"Error loading paper_list_3.py: {e}")

    # Load paper_list_4
    try:
        paper_list_4_path = os.path.join(scripts_dir, "paper_list_4.py")
        # First fix the import issue in paper_list_4.py
        with open(paper_list_4_path, 'r') as file:
            content = file.read()

        # If it's trying to import serverless_papers which doesn't exist
        if "from paper_list_3 import serverless_papers" in content:
            # Read the content of paper_list_4 and modify it
            modified_content = content.replace(
                "from paper_list_3 import serverless_papers",
                "# Import disabled: papers = []"
            )

            # Write to a temporary file
            temp_path = os.path.join(scripts_dir, "paper_list_4_temp.py")
            with open(temp_path, 'w') as file:
                file.write(modified_content)

            # Import from the temporary file
            paper_list_4 = import_module_from_path("paper_list_4_temp", temp_path)

            # Clean up
            os.remove(temp_path)
        else:
            paper_list_4 = import_module_from_path("paper_list_4", paper_list_4_path)

        # Try to get 'extended_papers' first, if not available try 'papers'
        papers4 = getattr(paper_list_4, "extended_papers", getattr(paper_list_4, "papers", []))
        print(f"Loaded {len(papers4)} papers from paper_list_4.py")

        for paper in papers4:
            paper["source"] = "paper_list_4"
            all_papers.append(paper)
    except Exception as e:
        print(f"Error loading paper_list_4.py: {e}")

    print(f"\nTotal papers loaded: {len(all_papers)}")
    return all_papers

def normalize_paper_structure(papers):
    """Normalize the structure of papers to ensure consistency."""
    normalized_papers = []

    for i, paper in enumerate(papers, 1):
        # Format keywords as a comma-separated string if they're in an array/list
        keywords = paper.get("keywords", "")
        if isinstance(keywords, list):
            keywords = ", ".join(keywords)

        normalized = {
            "consolidated_id": i,
            "title": paper.get("title", ""),
            # "authors": paper.get("authors", ""),
            "year": paper.get("year", ""),
            "venue": paper.get("venue", ""),
            "category": paper.get("category", ""),
            # "pdf_link": paper.get("pdf_link", paper.get("url", "")),
            # "doi": paper.get("doi", ""),
            "keywords": keywords,
            # "source_file": paper.get("source", "")
        }
        normalized_papers.append(normalized)

    return normalized_papers

def save_to_csv(papers, output_file):
    """Save the papers to a CSV file."""
    df = pd.DataFrame(papers)

    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # Save to CSV
    df.to_csv(output_file, index=False)
    print(f"Saved {len(papers)} papers to {output_file}")

    return df

def categorize_papers_by_metrics(papers):
    """Categorize papers by their main metrics/focus areas."""
    # Define metric keywords for categorization
    metric_keywords = {
        "Latency": ["latency", "cold start", "response time", "delay", "startup"],
        "Reliability & QoS": ["reliability", "qos", "quality of service", "fairness", "sla"],
        "Security & Privacy": ["security", "privacy", "authentication", "vulnerability"],
        "Cost": ["cost", "pricing", "economic", "billing", "financial"],
        "Energy Consumption": ["energy", "power", "consumption", "carbon", "green"],
        "Resource Management": ["resource", "scheduling", "allocation", "provisioning", "autoscaling"],
        "Benchmarking & Evaluation": ["benchmark", "evaluation", "performance", "test", "comparison"]
    }

    # Add metric flags to each paper
    for paper in papers:
        title = str(paper.get("title", "")).lower()
        category = str(paper.get("category", "")).lower()
        keywords = str(paper.get("keywords", "")).lower()

        # Combined text for searching
        combined_text = f"{title} {category} {keywords}"

        # Check each metric
        for metric, terms in metric_keywords.items():
            if any(term.lower() in combined_text for term in terms):
                paper[metric] = "Yes"
            else:
                paper[metric] = "No"

    return papers

def create_metric_summary(papers):
    """Create a summary of papers by metrics."""
    metrics = ["Latency", "Reliability & QoS", "Security & Privacy", "Cost",
               "Energy Consumption", "Resource Management", "Benchmarking & Evaluation"]

    summary = {}
    for metric in metrics:
        count = sum(1 for paper in papers if paper.get(metric) == "Yes")
        percentage = (count / len(papers)) * 100 if papers else 0
        summary[metric] = {
            "count": count,
            "percentage": f"{percentage:.1f}%"
        }

    # Create a DataFrame for the summary
    summary_data = []
    for metric, data in summary.items():
        summary_data.append({
            "Metric": metric,
            "Paper Count": data["count"],
            "Percentage": data["percentage"]
        })

    return pd.DataFrame(summary_data)

def main():
    # Set up paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir.endswith('scripts'):
        project_dir = os.path.dirname(script_dir)
    else:
        project_dir = script_dir
        script_dir = os.path.join(project_dir, 'scripts')

    results_dir = os.path.join(project_dir, 'results')

    # Load all papers
    all_papers = load_papers(script_dir)

    # Normalize paper structure
    normalized_papers = normalize_paper_structure(all_papers)

    # Categorize papers by metrics
    categorized_papers = categorize_papers_by_metrics(normalized_papers)

    # Save to CSV
    consolidated_csv = os.path.join(results_dir, 'consolidated_papers.csv')
    df = save_to_csv(categorized_papers, consolidated_csv)

    # Create and save metric summary
    summary_df = create_metric_summary(categorized_papers)
    summary_csv = os.path.join(results_dir, 'metrics_summary_consolidated.csv')
    summary_df.to_csv(summary_csv, index=False)
    print(f"Saved metrics summary to {summary_csv}")

    # Print summary
    print("\nMetrics Summary:")
    for _, row in summary_df.iterrows():
        print(f"  {row['Metric']}: {row['Paper Count']} papers ({row['Percentage']})")

    # Create filtered CSVs for each metric
    for metric in ["Latency", "Reliability & QoS", "Security & Privacy", "Cost",
                  "Energy Consumption", "Resource Management", "Benchmarking & Evaluation"]:
        # Filter papers by metric
        filtered_papers = [p for p in categorized_papers if p.get(metric) == "Yes"]

        # Create safe filename
        safe_metric = metric.lower().replace(" & ", "_").replace(" ", "_")
        filtered_csv = os.path.join(results_dir, f"{safe_metric}_papers_consolidated.csv")

        # Save filtered papers
        if filtered_papers:
            filtered_df = save_to_csv(filtered_papers, filtered_csv)

if __name__ == "__main__":
    main()
