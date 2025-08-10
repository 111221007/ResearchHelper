import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.table import Table
import sys
import os
sys.path.append('./scripts')

# Try to import all paper lists, handling any import errors gracefully
all_papers = []

try:
    from paper_list_1 import papers as papers1
    all_papers.extend(papers1)
    print(f"Loaded {len(papers1)} papers from paper_list_1")
except Exception as e:
    print(f"Warning: Could not load paper_list_1: {e}")
    papers1 = []

try:
    from paper_list_2 import papers as papers2
    all_papers.extend(papers2)
    print(f"Loaded {len(papers2)} papers from paper_list_2")
except Exception as e:
    print(f"Warning: Could not load paper_list_2: {e}")
    papers2 = []

try:
    from paper_list_3 import papers as papers3
    all_papers.extend(papers3)
    print(f"Loaded {len(papers3)} papers from paper_list_3")
except Exception as e:
    print(f"Warning: Could not load paper_list_3: {e}")
    papers3 = []

try:
    from paper_list_4 import extended_papers as papers4
    all_papers.extend(papers4)
    print(f"Loaded {len(papers4)} papers from paper_list_4")
except Exception as e:
    print(f"Warning: Could not load paper_list_4: {e}")
    papers4 = []

print(f"Total papers loaded: {len(all_papers)}")

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

# Build table data
rows = []
for paper in all_papers:
    metrics = infer_metrics(paper)
    row = {
        'id': paper.get('id', ''),
        'title': paper.get('title', ''),
    }
    row.update({m: 'yes' if metrics[m] else 'no' for m in metric_keywords})
    rows.append(row)

df = pd.DataFrame(rows)

# Display the table
print(df[["id", "title"] + list(metric_keywords.keys())].to_markdown(index=False))

# Generate table figure
fig, ax = plt.subplots(figsize=(18, min(1+len(df)*0.5, 100)))
ax.axis('off')
table = ax.table(cellText=df.values, colLabels=df.columns, loc='center', cellLoc='center', colLoc='center')
table.auto_set_font_size(False)
table.set_fontsize(10)
table.auto_set_column_width(col=list(range(len(df.columns))))
for (row, col), cell in table.get_celld().items():
    if row == 0:
        cell.set_fontsize(12)
        cell.set_text_props(weight='bold')
        cell.set_facecolor('#cccccc')
    if row % 2 == 0 and row != 0:
        cell.set_facecolor('#f9f9f9')
    if row % 2 == 1:
        cell.set_facecolor('#ffffff')
plt.title("Metrics Coverage Table (All Papers)", fontsize=16, weight='bold')
plt.tight_layout()

results_dir = os.path.join(os.path.dirname(__file__), '../results')
os.makedirs(results_dir, exist_ok=True)

plt.savefig(os.path.join(results_dir, "metrics_coverage_table_all.png"), dpi=300)
print(f"Figure saved as {os.path.join(results_dir, 'metrics_coverage_table_all.png')}")
plt.close()

df[["id", "title"] + list(metric_keywords.keys())].to_csv(os.path.join(results_dir, "metrics_coverage_table_all.csv"), index=False)
print(f"CSV saved as {os.path.join(results_dir, 'metrics_coverage_table_all.csv')}")
