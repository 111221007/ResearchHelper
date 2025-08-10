import pandas as pd
import matplotlib.pyplot as plt
import sys
import os
sys.path.append('./scripts')
from paper_list_1 import papers as papers1
from paper_list_2 import papers as papers2
from paper_list_3 import papers as papers3
from paper_list_4 import extended_papers as papers4
all_papers = papers1 + papers2 + papers3 + papers4

# Enhanced metric keywords for more comprehensive inference
metric_keywords = {
    "Latency": ["latency", "cold start", "response time", "tail latency", "startup time", "delay", "responsiveness", "warm-up", "initialization", "boot time"],
    "Reliability & QoS": ["reliability", "qos", "quality of service", "sla", "slo", "fairness", "availability", "fault tolerance", "consistency", "uptime", "service level", "dependability"],
    "Security & Privacy": ["security", "privacy", "attack", "vulnerability", "authentication", "authorization", "encryption", "threat", "malware", "breach", "confidentiality", "integrity"],
    "Cost": ["cost", "pricing", "revenue", "billing", "economic", "financial", "budget", "expense", "optimization", "savings", "efficiency"],
    "Energy Consumption": ["energy", "power", "co2", "green computing", "carbon", "consumption", "efficiency", "sustainable", "environmental", "electricity", "watt"],
    "Resource Management": ["resource", "scaling", "allocation", "orchestration", "container", "scheduling", "auto-scaling", "provisioning", "utilization", "deployment", "optimization"],
    "Benchmarking & Evaluation": ["benchmark", "evaluation", "suite", "comparison", "framework", "workload", "performance characterization", "testing", "measurement", "analysis", "assessment", "study"]
}

# Helper to infer metric coverage
def infer_metrics(paper):
    category = paper.get('category', '')
    keywords = paper.get('keywords', '')

    # Handle keywords as either string or list
    if isinstance(keywords, list):
        keywords = ', '.join(keywords)
    elif not isinstance(keywords, str):
        keywords = str(keywords)

    text = (category + ',' + keywords).lower()
    result = {}
    for metric, keywords_list in metric_keywords.items():
        result[metric] = any(kw in text for kw in keywords_list)
    return result

# Create results directory
results_dir = os.path.join(os.path.dirname(__file__), '../results')
os.makedirs(results_dir, exist_ok=True)

# Function to create individual metric table
def create_metric_table(metric_name, metric_keywords_list):
    print(f"\n=== Processing {metric_name} ===")

    # Filter papers that cover this specific metric
    relevant_papers = []
    for paper in all_papers:
        category = paper.get('category', '')
        keywords = paper.get('keywords', '')

        # Handle keywords as either string or list
        if isinstance(keywords, list):
            keywords = ', '.join(keywords)
        elif not isinstance(keywords, str):
            keywords = str(keywords)

        text = (category + ',' + keywords).lower()

        # Check if paper covers this metric
        if any(kw in text for kw in metric_keywords_list):
            relevant_papers.append(paper)

    print(f"Found {len(relevant_papers)} papers covering {metric_name}")

    if len(relevant_papers) == 0:
        print(f"No papers found for {metric_name}")
        return

    # Create DataFrame for this metric
    rows = []
    for paper in relevant_papers:
        row = {
            'id': paper.get('id', ''),
            'title': paper.get('title', ''),
            'authors': paper.get('authors', ''),
            'year': paper.get('year', ''),
            'venue': paper.get('venue', ''),
            'category': paper.get('category', ''),
            'pdf_link': paper.get('pdf_link', paper.get('url', ''))
        }
        rows.append(row)

    df = pd.DataFrame(rows)

    # Sort by year (newest first)
    df['year'] = pd.to_numeric(df['year'], errors='coerce')
    df = df.sort_values('year', ascending=False, na_position='last')

    # Save as CSV
    csv_filename = f"{metric_name.lower().replace(' & ', '_').replace(' ', '_')}_papers.csv"
    csv_path = os.path.join(results_dir, csv_filename)
    df.to_csv(csv_path, index=False)
    print(f"CSV saved: {csv_path}")

    # Create and save table figure
    fig, ax = plt.subplots(figsize=(20, min(2 + len(df) * 0.4, 50)))
    ax.axis('off')

    # Prepare data for table (limit title length for better display)
    display_df = df.copy()
    display_df['title'] = display_df['title'].apply(lambda x: x[:80] + '...' if len(str(x)) > 80 else x)

    table = ax.table(cellText=display_df.values, colLabels=display_df.columns,
                     loc='center', cellLoc='left', colLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.auto_set_column_width(col=list(range(len(display_df.columns))))

    # Style the table
    for (row, col), cell in table.get_celld().items():
        if row == 0:  # Header
            cell.set_fontsize(10)
            cell.set_text_props(weight='bold')
            cell.set_facecolor('#4CAF50')
            cell.set_text_props(color='white')
        elif row % 2 == 0:
            cell.set_facecolor('#f9f9f9')
        else:
            cell.set_facecolor('#ffffff')

    plt.title(f"{metric_name} - Serverless Computing Papers ({len(df)} papers)",
              fontsize=16, weight='bold', pad=20)
    plt.tight_layout()

    # Save figure
    png_filename = f"{metric_name.lower().replace(' & ', '_').replace(' ', '_')}_papers.png"
    png_path = os.path.join(results_dir, png_filename)
    plt.savefig(png_path, dpi=300, bbox_inches='tight')
    print(f"Figure saved: {png_path}")
    plt.close()

    # Print summary
    print(f"Years covered: {df['year'].min():.0f} - {df['year'].max():.0f}")
    print(f"Top venues: {df['venue'].value_counts().head(3).to_dict()}")
    print()

# Generate individual tables for each metric
print("Generating individual metric tables...")

for metric_name, keywords_list in metric_keywords.items():
    create_metric_table(metric_name, keywords_list)

print("=== Summary ===")
print("Individual metric tables generated successfully!")
print("Files saved in results/ directory:")
for metric_name in metric_keywords.keys():
    csv_name = f"{metric_name.lower().replace(' & ', '_').replace(' ', '_')}_papers.csv"
    png_name = f"{metric_name.lower().replace(' & ', '_').replace(' ', '_')}_papers.png"
    print(f"  - {csv_name}")
    print(f"  - {png_name}")
