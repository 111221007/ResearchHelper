#!/usr/bin/env python3
"""
Script to enhance serverless papers CSV with category analysis, keywords, contributions, and limitations.
"""

import pandas as pd
import re
from datetime import datetime
import os

def analyze_paper_content(title, abstract):
    """
    Analyze paper title and abstract to extract category, keywords, contributions, and limitations.
    """
    text = f"{title} {abstract}".lower()

    # Define category mapping based on specific categories requested
    categories = {
        'Survey': ['survey', 'review', 'taxonomy', 'comparative', 'literature review', 'systematic review', 'state of the art', 'overview', 'benchmark', 'benchmarking', 'evaluation', 'comparison', 'analysis'],
        'Latency': ['latency', 'delay', 'response time', 'cold start', 'warm start', 'startup time', 'execution time', 'tail latency'],
        'Reliability Security Privacy': ['reliability', 'security', 'privacy', 'authentication', 'authorization', 'encryption', 'fault tolerance', 'availability', 'trust', 'confidentiality', 'integrity'],
        'QoS': ['qos', 'quality of service', 'sla', 'service level agreement', 'performance guarantee', 'service quality'],
        'Cost': ['cost', 'billing', 'pricing', 'economic', 'budget', 'financial', 'expense', 'cost-effective', 'cost optimization'],
        'Energy Consumption': ['energy', 'power', 'consumption', 'sustainable', 'green', 'carbon', 'co2', 'efficiency', 'energy-aware', 'energy-efficient'],
        'Resource Management': ['resource', 'allocation', 'scheduling', 'scaling', 'autoscaling', 'utilization', 'capacity', 'provisioning', 'orchestration', 'placement']
    }

    # Find matching categories
    detected_categories = []
    for category, keywords in categories.items():
        if any(keyword in text for keyword in keywords):
            detected_categories.append(category)

    # If no specific category found, assign to "Others"
    if not detected_categories:
        detected_categories = ['Others']

    # Extract keywords based on common serverless terms
    keyword_patterns = {
        'cold start': ['cold start', 'cold-start'],
        'warm start': ['warm start', 'warm-start'],
        'autoscaling': ['autoscaling', 'auto-scaling', 'scaling'],
        'resource management': ['resource management', 'resource allocation'],
        'function placement': ['function placement', 'placement'],
        'performance optimization': ['performance optimization', 'optimization'],
        'serverless': ['serverless', 'faas', 'function as a service'],
        'containerization': ['container', 'containerization'],
        'microservices': ['microservices', 'micro-services'],
        'cloud computing': ['cloud computing', 'cloud'],
        'latency': ['latency', 'delay'],
        'throughput': ['throughput'],
        'elasticity': ['elasticity', 'elastic'],
        'multi-tenant': ['multi-tenant', 'multitenant'],
        'queuing': ['queue', 'queuing'],
        'load balancing': ['load balancing', 'load distribution'],
        'energy efficiency': ['energy', 'sustainable', 'co2'],
        'reinforcement learning': ['reinforcement learning', 'rl'],
        'deep learning': ['deep learning', 'neural network'],
        'prediction': ['prediction', 'predictive', 'forecasting'],
        'monitoring': ['monitoring', 'observability'],
        'deadline': ['deadline', 'time constraint'],
        'memory management': ['memory', 'memory management'],
        'cpu allocation': ['cpu', 'processor'],
        'distributed systems': ['distributed', 'cluster']
    }

    detected_keywords = []
    for keyword, patterns in keyword_patterns.items():
        if any(pattern in text for pattern in patterns):
            detected_keywords.append(keyword)

    # Extract contributions from abstract
    contributions = extract_contributions(abstract)

    # Extract limitations from abstract
    limitations = extract_limitations(abstract)

    return {
        'original_category': ', '.join(detected_categories),
        'original_keywords': ', '.join(detected_keywords) if detected_keywords else 'serverless computing',
        'contributions': contributions,
        'limitations': limitations
    }

def extract_contributions(abstract):
    """
    Extract key contributions from the abstract.
    """
    if not abstract or pd.isna(abstract):
        return "Not specified"

    text = abstract.lower()

    # Look for contribution indicators
    contribution_patterns = [
        r'we propose ([^.]+)',
        r'we introduce ([^.]+)',
        r'we present ([^.]+)',
        r'we show ([^.]+)',
        r'we develop ([^.]+)',
        r'we design ([^.]+)',
        r'we implement ([^.]+)',
        r'this paper introduces ([^.]+)',
        r'this paper presents ([^.]+)',
        r'this paper proposes ([^.]+)',
        r'our approach ([^.]+)',
        r'our method ([^.]+)',
        r'our framework ([^.]+)',
        r'our algorithm ([^.]+)',
        r'the proposed ([^.]+)',
        r'key contributions include ([^.]+)'
    ]

    contributions = []
    for pattern in contribution_patterns:
        matches = re.findall(pattern, text)
        contributions.extend(matches)

    # Also look for specific achievements/improvements
    improvement_patterns = [
        r'(\d+%?\s*improvement)',
        r'(\d+%?\s*reduction)',
        r'(\d+%?\s*increase)',
        r'(\d+x\s*better)',
        r'(\d+x\s*improvement)',
        r'up to (\d+%?\s*\w+)',
        r'reduces?\s+([^.]+by\s+\d+%?[^.]*)',
        r'improves?\s+([^.]+by\s+\d+%?[^.]*)'
    ]

    improvements = []
    for pattern in improvement_patterns:
        matches = re.findall(pattern, text)
        improvements.extend(matches)

    # Combine and clean contributions
    all_contributions = contributions + improvements
    if all_contributions:
        # Clean and limit length
        cleaned = [contrib.strip().capitalize() for contrib in all_contributions[:3]]
        return '; '.join(cleaned)

    # Fallback: extract first sentence that might indicate contribution
    sentences = abstract.split('.')
    for sentence in sentences[:3]:
        if any(word in sentence.lower() for word in ['propose', 'introduce', 'present', 'show', 'develop']):
            return sentence.strip().capitalize()

    return "Novel approach to serverless computing challenges"

def extract_limitations(abstract):
    """
    Extract limitations mentioned in the abstract.
    """
    if not abstract or pd.isna(abstract):
        return "Not specified"

    text = abstract.lower()

    # Look for limitation indicators
    limitation_patterns = [
        r'limitation[s]?\s+([^.]+)',
        r'challenge[s]?\s+([^.]+)',
        r'drawback[s]?\s+([^.]+)',
        r'constraint[s]?\s+([^.]+)',
        r'however[,]?\s+([^.]+)',
        r'but\s+([^.]+)',
        r'although\s+([^.]+)',
        r'despite\s+([^.]+)',
        r'problem[s]?\s+([^.]+)',
        r'issue[s]?\s+([^.]+)',
        r'difficult[y]?\s+([^.]+)',
        r'complex[ity]?\s+([^.]+)'
    ]

    limitations = []
    for pattern in limitation_patterns:
        matches = re.findall(pattern, text)
        limitations.extend(matches)

    if limitations:
        # Clean and limit
        cleaned = [limit.strip().capitalize() for limit in limitations[:2]]
        return '; '.join(cleaned)

    # Check for common serverless limitations
    common_limitations = [
        'cold start',
        'vendor lock-in',
        'debugging complexity',
        'monitoring challenges',
        'state management',
        'execution time limits',
        'resource constraints',
        'network latency',
        'scalability limits'
    ]

    found_limitations = [limit for limit in common_limitations if limit in text]
    if found_limitations:
        return '; '.join(found_limitations[:2]).title()

    return "Not explicitly mentioned"

def main():
    # Read the input CSV
    input_path = "/Users/reddy/2025/ResearchHelper/results/final/serverless_survey_papers_final_with_abstract.csv"

    if not os.path.exists(input_path):
        print(f"Error: File not found: {input_path}")
        return

    print(f"Reading CSV file: {input_path}")
    df = pd.read_csv(input_path)

    print(f"Processing {len(df)} papers...")

    # Process each paper
    results = []
    for idx, row in df.iterrows():
        # Handle NaN/null titles
        title = row['title'] if pd.notna(row['title']) else "Unknown Title"
        title_display = str(title)[:50] if title else "Unknown Title"

        print(f"Processing paper {idx + 1}/{len(df)}: {title_display}...")

        # Handle NaN/null abstracts
        abstract = row['abstract'] if pd.notna(row['abstract']) else ""

        analysis = analyze_paper_content(title, abstract)
        results.append(analysis)

    # Add new columns to dataframe
    df['original_category'] = [r['original_category'] for r in results]
    df['original_keywords'] = [r['original_keywords'] for r in results]
    df['contributions'] = [r['contributions'] for r in results]
    df['limitations'] = [r['limitations'] for r in results]

    # Generate output filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"/Users/reddy/2025/ResearchHelper/results/final/serverless_survey_papers_enhanced_{timestamp}.csv"

    # Save enhanced CSV
    df.to_csv(output_path, index=False)

    print(f"\nEnhanced CSV saved to: {output_path}")
    print(f"Added 4 new columns:")
    print("- original_category: Paper categorization")
    print("- original_keywords: Relevant keywords")
    print("- contributions: Paper contributions")
    print("- limitations: Paper limitations")

    # Display summary statistics
    print(f"\nSummary:")
    print(f"Total papers processed: {len(df)}")
    print(f"Categories found: {df['original_category'].nunique()}")
    print(f"Most common categories:")
    category_counts = {}
    for categories in df['original_category']:
        if pd.notna(categories):
            for cat in categories.split(', '):
                category_counts[cat] = category_counts.get(cat, 0) + 1

    for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  {cat}: {count} papers")

if __name__ == "__main__":
    main()
