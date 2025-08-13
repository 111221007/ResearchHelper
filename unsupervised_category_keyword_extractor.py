#!/usr/bin/env python3
"""
Unsupervised category and keyword extraction for research papers using BERTopic and KeyBERT.
Adds columns: original_category, original_keywords, contributions, limitations (and more).
"""
import os
import re
from datetime import datetime
import pandas as pd
from keybert import KeyBERT
from sentence_transformers import SentenceTransformer
from bertopic import BERTopic
from transformers import pipeline
import sys
import argparse

def extract_contributions(abstract: str) -> str:
    if not abstract or pd.isna(abstract):
        return "Not specified"
    text = abstract.lower()
    contribution_patterns = [
        r'we propose ([^.]+)', r'we introduce ([^.]+)', r'we present ([^.]+)', r'we show ([^.]+)',
        r'we develop ([^.]+)', r'we design ([^.]+)', r'we implement ([^.]+)', r'this paper introduces ([^.]+)',
        r'this paper presents ([^.]+)', r'this paper proposes ([.]+)', r'our approach ([^.]+)',
        r'our method ([^.]+)', r'our framework ([^.]+)', r'our algorithm ([^.]+)', r'the proposed ([^.]+)',
        r'key contributions include ([^.]+)'
    ]
    improvements = [
        r'(\d+%?\s*improvement)', r'(\d+%?\s*reduction)', r'(\d+%?\s*increase)', r'(\d+x\s*better)',
        r'(\d+x\s*improvement)', r'up to (\d+%?\s*\w+)', r'reduces?\s+([^.]+by\s+\d+%?[^.]*)',
        r'improves?\s+([^.]+by\s+\d+%?[^.]*)'
    ]
    hits = []
    for p in contribution_patterns:
        hits.extend(re.findall(p, text))
    for p in improvements:
        hits.extend(re.findall(p, text))
    if hits:
        cleaned = [h.strip().capitalize() for h in hits[:3]]
        return '; '.join(cleaned)
    for sentence in abstract.split('.')[:3]:
        if any(w in sentence.lower() for w in ['propose', 'introduce', 'present', 'show', 'develop']):
            return sentence.strip().capitalize()
    return "Novel approach to serverless computing challenges"

def extract_limitations(abstract: str) -> str:
    if not abstract or pd.isna(abstract):
        return "Not specified"
    text = abstract.lower()
    limitation_patterns = [
        r'limitation[s]?\s+([^.]+)', r'challenge[s]?\s+([^.]+)', r'drawback[s]?\s+([^.]+)',
        r'constraint[s]?\s+([^.]+)', r'however[,]?\s+([^.]+)', r'but\s+([^.]+)', r'although\s+([^.]+)',
        r'despite\s+([^.]+)', r'problem[s]?\s+([^.]+)', r'issue[s]?\s+([^.]+)', r'difficult[y]?\s+([^.]+)',
        r'complex[ity]?\s+([^.]+)'
    ]
    hits = []
    for p in limitation_patterns:
        hits.extend(re.findall(p, text))
    if hits:
        cleaned = [h.strip().capitalize() for h in hits[:2]]
        return '; '.join(cleaned)
    common = [
        'cold start', 'vendor lock-in', 'debugging complexity', 'monitoring challenges', 'state management',
        'execution time limits', 'resource constraints', 'network latency', 'scalability limits'
    ]
    found = [c for c in common if c in text]
    if found:
        return '; '.join(found[:2]).title()
    return "Not explicitly mentioned"

def build_about_summarizer():
    try:
        return pipeline("summarization", model="facebook/bart-large-cnn", device_map="auto")
    except Exception:
        return None

def summarize_about(summarizer, title: str, abstract: str) -> str:
    text = (abstract or "").strip() or (title or "").strip()
    if not text:
        return "Not specified"
    if summarizer is None:
        return text[:240]
    try:
        out = summarizer(text, max_length=80, min_length=30, do_sample=False)
        return out[0]["summary_text"].strip()
    except Exception:
        return text[:240].strip()

def unsupervised_categorize_keywords(df: pd.DataFrame) -> pd.DataFrame:
    docs = []
    rows_idx = []
    for i, row in df.iterrows():
        title = str(row.get("title", "") or "")
        abstract = str(row.get("abstract", "") or "")
        text = (title + ". " + abstract).strip()
        docs.append(text if text else "No content")
        rows_idx.append(i)
    emb_model = SentenceTransformer("all-MiniLM-L6-v2")
    topic_model = BERTopic(language="english", calculate_probabilities=True, verbose=True, embedding_model=emb_model)
    topics, probs = topic_model.fit_transform(docs)
    topic_model.generate_topic_labels(nr_words=3, topic_prefix=False, word_length=1)
    info = topic_model.get_topic_info()
    topic_lookup = {}
    for _, r in info.iterrows():
        tid = int(r["Topic"])
        label = str(r["Name"])
        words = topic_model.get_topic(tid) or []
        kw = ", ".join([w for w, s in words[:8]]) if words else ""
        topic_lookup[tid] = (label, kw)
    kw_model = KeyBERT(model=emb_model)
    summarizer = build_about_summarizer()
    topic_ids, topic_labels, topic_keywords, doc_keywords, abouts, contributions, limitations = [], [], [], [], [], [], []
    for local_idx, row_idx in enumerate(rows_idx):
        row = df.loc[row_idx]
        title = str(row.get("title", "") or "")
        abstract = str(row.get("abstract", "") or "")
        text = (title + ". " + abstract).strip()
        tid = int(topics[local_idx])
        label, tkw = topic_lookup.get(tid, ("Misc", ""))
        topic_ids.append(tid)
        topic_labels.append(label)
        topic_keywords.append(tkw)
        if text and text != "No content":
            try:
                kws = kw_model.extract_keywords(text, keyphrase_ngram_range=(1, 2), stop_words="english", top_n=8, use_mmr=True, diversity=0.6)
                dockw = ", ".join([k for k, _ in kws]) if kws else ""
            except Exception:
                dockw = ""
        else:
            dockw = ""
        doc_keywords.append(dockw if dockw else "serverless computing")
        abouts.append(summarize_about(summarizer, title, abstract))
        contributions.append(extract_contributions(abstract))
        limitations.append(extract_limitations(abstract))
    df.loc[rows_idx, "original_category"] = topic_labels
    df.loc[rows_idx, "original_keywords"] = doc_keywords
    df.loc[rows_idx, "contributions"] = contributions
    df.loc[rows_idx, "limitations"] = limitations
    return df

def main():
    parser = argparse.ArgumentParser(description="Unsupervised category/keyword extraction for research papers")
    parser.add_argument('--input', type=str, help='Input CSV file path', required=False)
    parser.add_argument('--output', type=str, help='Output CSV file path', required=False)
    args = parser.parse_args()

    if args.input:
        input_path = args.input
    else:
        input_path = "/Users/reddy/2025/ResearchHelper/results/final/serverless_survey_papers_final_with_abstract.csv"
    if args.output:
        output_path = args.output
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"/Users/reddy/2025/ResearchHelper/results/final/serverless_survey_papers_unsupervised_{timestamp}.csv"

    if not os.path.exists(input_path):
        print(f"Error: File not found: {input_path}")
        return

    print(f"Reading CSV file: {input_path}")
    df = pd.read_csv(input_path)
    print(f"Processing {len(df)} papers...")
    df = unsupervised_categorize_keywords(df)
    # Save
    df.to_csv(output_path, index=False)
    print(f"\nEnhanced CSV saved to: {output_path}")
    print(f"Added columns: original_category, original_keywords, contributions, limitations")

if __name__ == "__main__":
    main()
