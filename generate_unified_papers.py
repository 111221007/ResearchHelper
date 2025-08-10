"""
Script to generate a complete unified collection of all papers
"""
import sys
import os

# Add scripts directory to path
sys.path.append('./scripts')

def load_all_papers():
    """Load papers from all paper list files"""
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
                "source_list": "paper_list_1",
                "metrics": paper.get('metrics', ''),
                "abstract": paper.get('abstract', ''),
                "notes": paper.get('notes', '')
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
                "source_list": "paper_list_2",
                "metrics": paper.get('metrics', ''),
                "abstract": paper.get('abstract', ''),
                "notes": paper.get('notes', '')
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
                "source_list": "paper_list_3",
                "metrics": paper.get('metrics', ''),
                "abstract": paper.get('abstract', ''),
                "notes": paper.get('notes', '')
            }
            all_papers.append(normalized)
        print(f"Loaded {len(papers3)} papers from paper_list_3")
    except Exception as e:
        print(f"Could not load paper_list_3: {e}")

    # Load from paper_list_4
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
                "source_list": "paper_list_4",
                "metrics": paper.get('metrics', ''),
                "abstract": paper.get('abstract', ''),
                "notes": paper.get('notes', '')
            }
            all_papers.append(normalized)
        print(f"Loaded {len(papers4)} papers from paper_list_4")
    except Exception as e:
        print(f"Could not load paper_list_4: {e}")

    return all_papers

def generate_unified_file():
    """Generate the complete unified file with all papers"""
    papers = load_all_papers()

    # Remove duplicates based on title
    unique_papers = []
    seen_titles = set()

    for paper in papers:
        title_clean = paper['title'].lower().strip()
        if title_clean and title_clean not in seen_titles:
            seen_titles.add(title_clean)
            unique_papers.append(paper)

    # Reassign unified IDs after deduplication
    for i, paper in enumerate(unique_papers):
        paper['unified_id'] = i + 1

    print(f"\nTotal papers after deduplication: {len(unique_papers)}")

    # Generate the Python file content
    file_content = '''"""
Comprehensive Unified Collection of All Serverless Computing Research Papers
==========================================================================

This file contains all papers from paper_list_1, paper_list_2, paper_list_3, and paper_list_4
combined into a single collection with standardized fields.

Total papers: ''' + str(len(unique_papers)) + '''

Fields included for each paper:
- unified_id: Unique sequential ID across all papers
- original_id: Original ID from source list
- title: Paper title
- authors: Paper authors
- year: Publication year
- venue: Publication venue/conference/journal
- category: Research category/area
- keywords: Keywords (string or list)
- pdf_link: Link to PDF
- doi: DOI identifier
- source_list: Which original list this paper came from
- metrics: Performance metrics (if available)
- abstract: Paper abstract (if available)
- notes: Additional notes (if available)
"""

# Comprehensive collection of all papers
papers = [
'''

    # Add all papers to the file content
    for paper in unique_papers:
        file_content += f'''    {{
        "unified_id": {paper['unified_id']},
        "original_id": {repr(paper['original_id'])},
        "title": {repr(paper['title'])},
        "authors": {repr(paper['authors'])},
        "year": {repr(paper['year'])},
        "venue": {repr(paper['venue'])},
        "category": {repr(paper['category'])},
        "keywords": {repr(paper['keywords'])},
        "pdf_link": {repr(paper['pdf_link'])},
        "doi": {repr(paper['doi'])},
        "source_list": {repr(paper['source_list'])},
        "metrics": {repr(paper['metrics'])},
        "abstract": {repr(paper['abstract'])},
        "notes": {repr(paper['notes'])}
    }},
'''

    file_content += ''']

# Enhanced metric keywords for classification
metric_keywords = {
    "Latency": ["latency", "cold start", "response time", "tail latency", "startup time", "delay", "responsiveness", "warm-up", "initialization", "boot time"],
    "Reliability & QoS": ["reliability", "qos", "quality of service", "sla", "slo", "fairness", "availability", "fault tolerance", "consistency", "uptime", "service level", "dependability"],
    "Security & Privacy": ["security", "privacy", "attack", "vulnerability", "authentication", "authorization", "encryption", "threat", "malware", "breach", "confidentiality", "integrity"],
    "Cost": ["cost", "pricing", "revenue", "billing", "economic", "financial", "budget", "expense", "optimization", "savings", "efficiency"],
    "Energy Consumption": ["energy", "power", "co2", "green computing", "carbon", "consumption", "efficiency", "sustainable", "environmental", "electricity", "watt"],
    "Resource Management": ["resource", "scaling", "allocation", "orchestration", "container", "scheduling", "auto-scaling", "provisioning", "utilization", "deployment", "optimization"],
    "Benchmarking & Evaluation": ["benchmark", "evaluation", "suite", "comparison", "framework", "workload", "performance characterization", "testing", "measurement", "analysis", "assessment", "study"]
}

def classify_paper_metrics(paper):
    """Classify a paper across all metrics based on its content"""
    category = str(paper.get('category', '')).lower()
    keywords = str(paper.get('keywords', '')).lower()
    title = str(paper.get('title', '')).lower()
    
    # Combine all text for analysis
    text = f"{category} {keywords} {title}"
    
    classification = {}
    for metric, metric_keywords_list in metric_keywords.items():
        classification[metric] = any(kw in text for kw in metric_keywords_list)
    
    return classification

def get_statistics():
    """Get statistics about the paper collection"""
    total_papers = len(papers)
    
    # Count by source
    source_counts = {}
    for paper in papers:
        source = paper['source_list']
        source_counts[source] = source_counts.get(source, 0) + 1
    
    # Count by year
    year_counts = {}
    for paper in papers:
        year = paper['year']
        if year:
            year_counts[year] = year_counts.get(year, 0) + 1
    
    # Count by category
    category_counts = {}
    for paper in papers:
        category = paper['category']
        if category:
            category_counts[category] = category_counts.get(category, 0) + 1
    
    return {
        'total_papers': total_papers,
        'source_counts': source_counts,
        'year_counts': year_counts,
        'category_counts': category_counts
    }

# Print summary when imported
print(f"✅ Unified Papers Collection: {len(papers)} papers loaded")
print("📚 Import this file using: from all_papers_unified import papers")
print("🔧 Available functions: get_statistics(), classify_paper_metrics(paper)")

if __name__ == "__main__":
    stats = get_statistics()
    print(f"\n=== COLLECTION STATISTICS ===")
    print(f"Total papers: {stats['total_papers']}")
    print(f"Source distribution: {stats['source_counts']}")
    years = [y for y in stats['year_counts'].keys() if y]
    if years:
        print(f"Year range: {min(years)} - {max(years)}")
    
    print(f"\nTop 10 categories:")
    for cat, count in sorted(stats['category_counts'].items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {cat}: {count} papers")
'''

    # Write to file
    with open('scripts/temp/all_papers_unified.py', 'w', encoding='utf-8') as f:
        f.write(file_content)

    return unique_papers

if __name__ == "__main__":
    papers = generate_unified_file()
