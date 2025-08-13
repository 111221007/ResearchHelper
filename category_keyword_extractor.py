#!/usr/bin/env python3
"""
Category and Keyword Extractor for Research Papers
Analyzes papers to extract categories, keywords, contributions, and limitations
"""

import pandas as pd
import re
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging
from collections import Counter
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize

# Download required NLTK data (run once)
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')

class CategoryKeywordExtractor:
    def __init__(self, output_dir: str = "/Users/reddy/2025/ResearchHelper/results"):
        self.output_dir = output_dir

        # Setup logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

        # Define categories and their keywords
        self.category_keywords = {
            'Survey': {
                'keywords': ['survey', 'review', 'systematic review', 'literature review', 'taxonomy',
                           'classification', 'comprehensive review', 'state of the art', 'overview'],
                'weight': 2.0
            },
            'Latency': {
                'keywords': ['latency', 'cold start', 'warm start', 'startup time', 'boot time',
                           'initialization', 'response time', 'delay', 'startup latency', 'cold boot'],
                'weight': 1.5
            },
            'Reliability': {
                'keywords': ['reliability', 'fault tolerance', 'fault recovery', 'availability',
                           'resilience', 'qos', 'quality of service', 'uptime', 'failure recovery'],
                'weight': 1.5
            },
            'Security': {
                'keywords': ['security', 'privacy', 'authentication', 'authorization', 'encryption',
                           'access control', 'data protection', 'secure computing', 'vulnerability'],
                'weight': 1.5
            },
            'Cost': {
                'keywords': ['cost', 'pricing', 'billing', 'economic', 'budget', 'expense',
                           'cost optimization', 'cost effective', 'pay per use', 'financial'],
                'weight': 1.5
            },
            'Energy Consumption': {
                'keywords': ['energy', 'power', 'consumption', 'efficiency', 'green computing',
                           'carbon footprint', 'sustainable', 'power efficiency', 'energy saving'],
                'weight': 1.5
            },
            'Resource Management': {
                'keywords': ['resource management', 'scaling', 'auto scaling', 'allocation',
                           'load balancing', 'resource allocation', 'capacity planning', 'optimization'],
                'weight': 1.5
            },
            'Benchmarking': {
                'keywords': ['benchmark', 'evaluation', 'performance evaluation', 'comparison',
                           'testing', 'measurement', 'metrics', 'assessment', 'analysis'],
                'weight': 1.3
            }
        }

        # Common serverless and cloud computing keywords
        self.serverless_keywords = [
            'serverless', 'faas', 'function as a service', 'lambda', 'azure functions',
            'google cloud functions', 'cloud computing', 'microservices', 'container',
            'kubernetes', 'docker', 'event driven', 'stateless'
        ]

        # Stop words for keyword extraction
        self.stop_words = set(stopwords.words('english'))
        self.stop_words.update(['paper', 'study', 'research', 'approach', 'method', 'system',
                               'application', 'work', 'result', 'conclusion', 'analysis'])

    def preprocess_text(self, text: str) -> str:
        """Preprocess text for analysis"""
        if not text:
            return ""

        # Convert to lowercase and remove special characters
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        # Remove extra whitespace
        text = ' '.join(text.split())
        return text

    def extract_keywords_from_text(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract relevant keywords from text"""
        if not text:
            return []

        # Tokenize and filter
        words = word_tokenize(self.preprocess_text(text))
        words = [word for word in words if word not in self.stop_words and len(word) > 2]

        # Count frequency
        word_counts = Counter(words)

        # Get most common words
        common_words = [word for word, count in word_counts.most_common(max_keywords * 2)]

        # Filter for relevance (prefer compound terms and technical terms)
        relevant_words = []
        for word in common_words:
            if (len(word) > 4 or
                word in self.serverless_keywords or
                any(keyword in word for cat_data in self.category_keywords.values()
                    for keyword in cat_data['keywords'])):
                relevant_words.append(word)

        return relevant_words[:max_keywords]

    def categorize_paper(self, title: str, abstract: str) -> Dict:
        """Categorize paper based on title and abstract"""
        combined_text = f"{title} {abstract}".lower()

        category_scores = {}
        matched_keywords = {}

        # Calculate scores for each category
        for category, data in self.category_keywords.items():
            score = 0
            found_keywords = []

            for keyword in data['keywords']:
                if keyword.lower() in combined_text:
                    score += data['weight']
                    found_keywords.append(keyword)

            if score > 0:
                category_scores[category] = score
                matched_keywords[category] = found_keywords

        # Determine primary category
        if category_scores:
            primary_category = max(category_scores, key=category_scores.get)
            primary_keywords = matched_keywords[primary_category]

            # Include secondary categories if scores are close
            sorted_categories = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
            categories = [primary_category]

            for cat, score in sorted_categories[1:]:
                if score >= category_scores[primary_category] * 0.7:  # Within 70% of top score
                    categories.append(cat)
                    primary_keywords.extend(matched_keywords[cat])

            return {
                'original_category': ', '.join(categories),
                'original_keywords': ', '.join(set(primary_keywords))
            }
        else:
            # Default category
            extracted_keywords = self.extract_keywords_from_text(combined_text, 5)
            return {
                'original_category': 'Others',
                'original_keywords': ', '.join(extracted_keywords[:3]) if extracted_keywords else 'serverless, cloud computing'
            }

    def extract_contributions(self, abstract: str) -> str:
        """Extract contributions from abstract using pattern matching"""
        if not abstract:
            return 'Not available'

        sentences = sent_tokenize(abstract)
        contribution_sentences = []

        # Patterns that indicate contributions
        contribution_patterns = [
            r'\b(?:we|this\s+(?:paper|work|study|research))\s+(?:propose|present|introduce|develop|design|implement|show|demonstrate|provide|offer|contribute)\b',
            r'\b(?:our|the)\s+(?:approach|method|system|framework|algorithm|technique|solution)\b',
            r'\bnov(?:el|elty)\b.*?\b(?:approach|method|system|framework|algorithm|technique|solution)\b',
            r'\bmain\s+contribution(?:s)?\b',
            r'\bkey\s+(?:contribution|finding|result|insight)\b',
            r'\b(?:first|new|novel)\s+(?:approach|method|system|framework)\b'
        ]

        for sentence in sentences:
            sentence_lower = sentence.lower()
            for pattern in contribution_patterns:
                if re.search(pattern, sentence_lower):
                    contribution_sentences.append(sentence.strip())
                    break

        if contribution_sentences:
            # Limit to 2 most relevant sentences
            return '. '.join(contribution_sentences[:2])
        else:
            # Fallback: look for sentences with key verbs
            fallback_verbs = ['propose', 'present', 'introduce', 'develop', 'design', 'implement', 'show', 'demonstrate']
            for sentence in sentences:
                if any(verb in sentence.lower() for verb in fallback_verbs):
                    return sentence.strip()

            return 'Not explicitly mentioned'

    def extract_limitations(self, abstract: str) -> str:
        """Extract limitations from abstract using pattern matching"""
        if not abstract:
            return 'Not explicitly mentioned'

        sentences = sent_tokenize(abstract)
        limitation_sentences = []

        # Patterns that indicate limitations
        limitation_patterns = [
            r'\blimitation(?:s)?\b',
            r'\bdrawback(?:s)?\b',
            r'\bweakness(?:es)?\b',
            r'\bchallenge(?:s)?\b',
            r'\bconstraint(?:s)?\b',
            r'\bissue(?:s)?\b',
            r'\bproblem(?:s)?\b',
            r'\bhowever\b',
            r'\bunfortunately\b',
            r'\bdifficult(?:y|ies)?\b',
            r'\bbarrier(?:s)?\b',
            r'\bobstacle(?:s)?\b'
        ]

        for sentence in sentences:
            sentence_lower = sentence.lower()
            for pattern in limitation_patterns:
                if re.search(pattern, sentence_lower):
                    limitation_sentences.append(sentence.strip())
                    break

        if limitation_sentences:
            # Limit to 2 most relevant sentences
            return '. '.join(limitation_sentences[:2])
        else:
            return 'Not explicitly mentioned'

    def process_papers_csv(self, csv_path: str) -> str:
        """Process papers CSV and add category/keyword information"""
        # Read the CSV
        df = pd.read_csv(csv_path)
        self.logger.info(f"Processing {len(df)} papers for categorization and keyword extraction")

        # Initialize columns if they don't exist
        if 'original_category' not in df.columns:
            df['original_category'] = ''
        if 'original_keywords' not in df.columns:
            df['original_keywords'] = ''
        if 'contributions' not in df.columns:
            df['contributions'] = ''
        if 'limitations' not in df.columns:
            df['limitations'] = ''

        # Process each paper
        for idx, row in df.iterrows():
            title = str(row.get('title', ''))
            abstract = str(row.get('abstract', ''))

            # Skip if already processed (has category)
            if row.get('original_category') and row.get('original_category') != '':
                continue

            self.logger.info(f"Processing paper {idx+1}/{len(df)}: {title[:50]}...")

            # Categorize and extract keywords
            category_info = self.categorize_paper(title, abstract)
            df.at[idx, 'original_category'] = category_info['original_category']
            df.at[idx, 'original_keywords'] = category_info['original_keywords']

            # Extract contributions and limitations
            contributions = self.extract_contributions(abstract)
            limitations = self.extract_limitations(abstract)

            df.at[idx, 'contributions'] = contributions
            df.at[idx, 'limitations'] = limitations

            # Progress update
            if (idx + 1) % 20 == 0:
                self.logger.info(f"Processed {idx+1}/{len(df)} papers")

        # Save the enhanced CSV
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"papers_with_categories_keywords_{timestamp}.csv"
        output_path = os.path.join(self.output_dir, output_filename)
        df.to_csv(output_path, index=False)

        # Print summary
        self.print_categorization_summary(df)
        self.logger.info(f"Enhanced CSV with categories and keywords saved to: {output_path}")

        return output_path

    def print_categorization_summary(self, df: pd.DataFrame):
        """Print categorization summary statistics"""
        print(f"\n📊 CATEGORIZATION SUMMARY:")
        print(f"Total papers processed: {len(df)}")

        # Category distribution
        categories = df['original_category'].value_counts()
        print(f"\n📂 CATEGORY DISTRIBUTION:")
        for category, count in categories.head(10).items():
            percentage = (count / len(df)) * 100
            print(f"  {category}: {count} papers ({percentage:.1f}%)")

        # Papers with contributions/limitations
        papers_with_contributions = len(df[df['contributions'] != 'Not explicitly mentioned'])
        papers_with_limitations = len(df[df['limitations'] != 'Not explicitly mentioned'])

        print(f"\n📈 CONTENT ANALYSIS:")
        print(f"Papers with identified contributions: {papers_with_contributions} ({papers_with_contributions/len(df)*100:.1f}%)")
        print(f"Papers with identified limitations: {papers_with_limitations} ({papers_with_limitations/len(df)*100:.1f}%)")

        # Most common keywords
        all_keywords = []
        for keywords_str in df['original_keywords']:
            if keywords_str and str(keywords_str) != 'nan':
                keywords = [k.strip() for k in str(keywords_str).split(',')]
                all_keywords.extend(keywords)

        keyword_counts = Counter(all_keywords)
        print(f"\n🔑 TOP KEYWORDS:")
        for keyword, count in keyword_counts.most_common(10):
            if keyword and keyword != '':
                print(f"  {keyword}: {count} papers")

def analyze_paper_content(title, abstract):
    """
    Analyze paper title and abstract to extract category, keywords, contributions, and limitations.
    (Imported from 04_category_key_word_extractor.py)
    """
    text = f"{title} {abstract}".lower()
    categories = {
        'Survey': ['survey', 'review', 'taxonomy', 'comparative', 'literature review', 'systematic review', 'state of the art', 'overview', 'benchmark', 'benchmarking', 'evaluation', 'comparison', 'analysis'],
        'Latency': ['latency', 'delay', 'response time', 'cold start', 'warm start', 'startup time', 'execution time', 'tail latency'],
        'Reliability Security Privacy': ['reliability', 'security', 'privacy', 'authentication', 'authorization', 'encryption', 'fault tolerance', 'availability', 'trust', 'confidentiality', 'integrity'],
        'QoS': ['qos', 'quality of service', 'sla', 'service level agreement', 'performance guarantee', 'service quality'],
        'Cost': ['cost', 'billing', 'pricing', 'economic', 'budget', 'financial', 'expense', 'cost-effective', 'cost optimization'],
        'Energy Consumption': ['energy', 'power', 'consumption', 'sustainable', 'green', 'carbon', 'co2', 'efficiency', 'energy-aware', 'energy-efficient'],
        'Resource Management': ['resource', 'allocation', 'scheduling', 'scaling', 'autoscaling', 'utilization', 'capacity', 'provisioning', 'orchestration', 'placement']
    }
    detected_categories = []
    for category, keywords in categories.items():
        if any(keyword in text for keyword in keywords):
            detected_categories.append(category)
    if not detected_categories:
        detected_categories = ['Others']
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
    # Use the class methods for contributions and limitations
    extractor = CategoryKeywordExtractor()
    contributions = extractor.extract_contributions(abstract)
    limitations = extractor.extract_limitations(abstract)
    return {
        'original_category': ', '.join(detected_categories),
        'original_keywords': ', '.join(detected_keywords) if detected_keywords else 'serverless computing',
        'contributions': contributions,
        'limitations': limitations
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python category_keyword_extractor.py <csv_file_path>")
        sys.exit(1)
    csv_file_path = sys.argv[1]
    extractor = CategoryKeywordExtractor()
    output_path = extractor.process_papers_csv(csv_file_path)
    print(f"Enhanced CSV saved to: {output_path}")
