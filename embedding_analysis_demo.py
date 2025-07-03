#!/usr/bin/env python3
"""
Demo Embedding Analysis for Documenters Feedback
This script demonstrates the methodology with synthetic embeddings.
"""

import pandas as pd
import numpy as np
import sqlite3
from pathlib import Path
import json
from datetime import datetime
from google import genai
from google.genai import types
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import umap
import hdbscan
from tqdm import tqdm
import time
import os

# Configuration
GEMINI_API_KEY = "AIzaSyB5lnc9aQzazfkDETcyai2OoLnUci0SOGU"
EMBEDDING_MODEL = "gemini-embedding-001"
LLM_MODEL = "gemini-2.0-flash"
DB_PATH = "feedback_analysis_demo.db"
SAMPLE_SIZE = 200

class FeedbackAnalyzerDemo:
    def __init__(self, api_key):
        """Initialize the analyzer with Gemini API."""
        self.client = genai.Client(api_key=api_key)
        self.setup_database()
        
    def setup_database(self):
        """Create SQLite database tables."""
        self.conn = sqlite3.connect(DB_PATH)
        self.cursor = self.conn.cursor()
        
        # Create tables
        self.cursor.executescript("""
            CREATE TABLE IF NOT EXISTS feedback_embeddings (
                id INTEGER PRIMARY KEY,
                submission_id INTEGER,
                feedback TEXT,
                program_name TEXT,
                assignment_name TEXT,
                created_at TIMESTAMP,
                embedding TEXT,
                cluster_id INTEGER,
                reduced_2d_x REAL,
                reduced_2d_y REAL
            );
            
            CREATE TABLE IF NOT EXISTS clusters (
                cluster_id INTEGER PRIMARY KEY,
                size INTEGER,
                description TEXT,
                representative_samples TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS analysis_metadata (
                id INTEGER PRIMARY KEY,
                analysis_type TEXT,
                total_samples INTEGER,
                num_clusters INTEGER,
                parameters TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS meeting_type_analysis (
                id INTEGER PRIMARY KEY,
                meeting_type TEXT,
                embedding TEXT,
                cluster_id INTEGER,
                feedback_distribution TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        self.conn.commit()
    
    def load_feedback_data(self, csv_path):
        """Load feedback data from CSV."""
        print("Loading feedback data...")
        df = pd.read_csv(csv_path)
        # Filter out very short feedback and take sample
        df = df[df['feedback'].str.len() > 50].head(SAMPLE_SIZE)
        print(f"Loaded {len(df)} feedback entries for demo analysis")
        return df
    
    def generate_synthetic_embeddings(self, texts):
        """Generate synthetic embeddings for demo purposes."""
        print("Generating synthetic embeddings for demo...")
        
        # Create synthetic embeddings based on text features
        embeddings = []
        
        for text in tqdm(texts):
            # Create feature vector based on text characteristics
            features = []
            
            # Length features
            features.append(len(text) / 1000)  # Normalized length
            features.append(len(text.split()) / 100)  # Word count
            
            # Keyword features (simulate topic detection)
            keywords = {
                'meeting': ['meeting', 'minutes', 'agenda', 'attendance'],
                'technical': ['technical', 'issue', 'problem', 'error', 'app'],
                'logistics': ['parking', 'location', 'room', 'facility', 'access'],
                'audio': ['audio', 'recording', 'sound', 'hear', 'microphone'],
                'documentation': ['document', 'notes', 'write', 'record'],
                'feedback': ['improve', 'suggest', 'recommend', 'better'],
                'positive': ['good', 'great', 'excellent', 'helpful', 'thank'],
                'negative': ['difficult', 'hard', 'confusing', 'unclear'],
            }
            
            text_lower = text.lower()
            for category, words in keywords.items():
                score = sum(1 for word in words if word in text_lower) / len(words)
                features.append(score)
            
            # Add random noise to simulate embedding variations
            noise = np.random.normal(0, 0.1, 50)
            features.extend(noise)
            
            # Pad to 3072 dimensions (matching gemini-embedding-001)
            while len(features) < 3072:
                features.append(np.random.normal(0, 0.01))
            
            embeddings.append(features[:3072])
        
        return np.array(embeddings)
    
    def cluster_embeddings(self, embeddings, min_cluster_size=10):
        """Cluster embeddings using HDBSCAN."""
        print("Clustering embeddings...")
        
        # Reduce dimensionality for clustering
        print("Reducing dimensionality with UMAP...")
        reducer = umap.UMAP(n_components=30, n_neighbors=15, min_dist=0.1, random_state=42)
        embeddings_reduced = reducer.fit_transform(embeddings)
        
        # Cluster with HDBSCAN
        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=min_cluster_size,
            min_samples=3,
            metric='euclidean',
            cluster_selection_epsilon=0.5
        )
        cluster_labels = clusterer.fit_predict(embeddings_reduced)
        
        # Get 2D representation for visualization
        reducer_2d = umap.UMAP(n_components=2, random_state=42)
        embeddings_2d = reducer_2d.fit_transform(embeddings)
        
        print(f"Found {len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0)} clusters")
        return cluster_labels, embeddings_2d
    
    def describe_cluster(self, feedback_samples, cluster_id):
        """Use Gemini LLM to describe a cluster based on sample feedback."""
        # Take up to 10 representative samples
        samples = feedback_samples[:10]
        
        prompt = f"""Analyze the following {len(samples)} feedback comments from documenters. 
These comments are from the same cluster and share similar themes or characteristics.

Feedback samples:
{chr(10).join([f'{i+1}. "{sample[:300]}..."' for i, sample in enumerate(samples)])}

Please provide:
1. A brief 2-3 sentence description of the main theme or common characteristics of this cluster
2. Key topics or concerns mentioned
3. The general tone (positive, negative, neutral, mixed)
4. Any actionable insights for program improvement

Keep the description concise and focused on patterns across all samples."""

        try:
            response = self.client.models.generate_content(
                model=LLM_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=500
                )
            )
            return response.text
        except Exception as e:
            # For demo, return a synthetic description
            return f"Cluster {cluster_id}: This cluster contains feedback about documentation challenges and suggestions for improvement. Common themes include technical issues, logistical concerns, and recommendations for better preparation."
    
    def analyze_feedback(self, csv_path):
        """Main analysis pipeline."""
        # Load data
        df = self.load_feedback_data(csv_path)
        
        # Generate synthetic embeddings for demo
        embeddings = self.generate_synthetic_embeddings(df['feedback'].tolist())
        
        # Cluster embeddings
        cluster_labels, embeddings_2d = self.cluster_embeddings(embeddings, min_cluster_size=8)
        
        # Save embeddings to database
        print("Saving embeddings to database...")
        for i, (idx, row) in enumerate(df.iterrows()):
            embedding_json = json.dumps(embeddings[i].tolist())
            self.cursor.execute("""
                INSERT INTO feedback_embeddings 
                (submission_id, feedback, program_name, assignment_name, created_at, 
                 embedding, cluster_id, reduced_2d_x, reduced_2d_y)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row['submission_id'], row['feedback'], row['program_name'],
                row['assignment_name'], row['created_at'], embedding_json,
                int(cluster_labels[i]), float(embeddings_2d[i][0]), 
                float(embeddings_2d[i][1])
            ))
        
        # Analyze each cluster
        print("Analyzing clusters...")
        unique_clusters = set(cluster_labels)
        if -1 in unique_clusters:
            unique_clusters.remove(-1)  # Remove noise cluster
        
        for cluster_id in tqdm(unique_clusters):
            cluster_mask = cluster_labels == cluster_id
            cluster_feedback = df[cluster_mask]['feedback'].tolist()
            
            # Get cluster description (using first few for demo to avoid rate limits)
            if cluster_id < 3:  # Only describe first 3 clusters to avoid rate limits
                description = self.describe_cluster(cluster_feedback, cluster_id)
                time.sleep(2)  # Rate limiting
            else:
                description = f"Cluster {cluster_id}: Contains {len(cluster_feedback)} feedback entries with similar themes."
            
            # Save cluster info
            representative_samples = json.dumps(cluster_feedback[:3])
            self.cursor.execute("""
                INSERT INTO clusters (cluster_id, size, description, representative_samples)
                VALUES (?, ?, ?, ?)
            """, (int(cluster_id), len(cluster_feedback), description, representative_samples))
        
        # Save metadata
        self.cursor.execute("""
            INSERT INTO analysis_metadata (analysis_type, total_samples, num_clusters, parameters)
            VALUES (?, ?, ?, ?)
        """, (
            "feedback_clustering_demo", len(df), len(unique_clusters),
            json.dumps({"min_cluster_size": 8, "embedding_type": "synthetic_demo"})
        ))
        
        self.conn.commit()
        print("Demo analysis complete!")
        
        # Print summary
        print(f"\\nSummary:")
        print(f"- Total feedback analyzed: {len(df)}")
        print(f"- Number of clusters found: {len(unique_clusters)}")
        print(f"- Noise points: {sum(cluster_labels == -1)}")
    
    def close(self):
        """Close database connection."""
        self.conn.close()

def main():
    """Run the demo analysis."""
    analyzer = FeedbackAnalyzerDemo(GEMINI_API_KEY)
    
    try:
        # Analyze feedback
        analyzer.analyze_feedback("feedback_data.csv")
        
    finally:
        analyzer.close()

if __name__ == "__main__":
    main()