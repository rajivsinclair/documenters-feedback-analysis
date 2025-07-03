#!/usr/bin/env python3
"""
Embedding Analysis for Documenters Feedback
This script analyzes text feedback using Google Gemini embeddings and clustering.
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
GEMINI_API_KEY = "AIzaSyDPNCzGo0LXmSXXobTs45Mrxeq2kCYG_vg"
EMBEDDING_MODEL = "gemini-embedding-001"
LLM_MODEL = "gemini-2.0-flash"
DB_PATH = "feedback_analysis.db"
BATCH_SIZE = 100  # For embedding generation

class FeedbackAnalyzer:
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
            
            CREATE TABLE IF NOT EXISTS meeting_type_analysis (
                id INTEGER PRIMARY KEY,
                meeting_type TEXT,
                embedding TEXT,
                cluster_id INTEGER,
                feedback_distribution TEXT,
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
        """)
        self.conn.commit()
    
    def load_feedback_data(self, csv_path):
        """Load feedback data from CSV."""
        print("Loading feedback data...")
        df = pd.read_csv(csv_path)
        # Filter out very short feedback
        df = df[df['feedback'].str.len() > 50]
        print(f"Loaded {len(df)} feedback entries")
        return df
    
    def generate_embeddings(self, texts, batch_size=100):
        """Generate embeddings for a list of texts using Gemini."""
        embeddings = []
        
        print(f"Generating embeddings for {len(texts)} texts...")
        for i in tqdm(range(0, len(texts), batch_size)):
            batch = texts[i:i+batch_size]
            
            try:
                # Generate embeddings with retry logic
                retries = 3
                for attempt in range(retries):
                    try:
                        result = self.client.models.embed_content(
                            model=EMBEDDING_MODEL,
                            contents=batch,
                            config=types.EmbedContentConfig(task_type="CLUSTERING")
                        )
                        
                        for embedding in result.embeddings:
                            embeddings.append(embedding.values)
                        break
                    except Exception as e:
                        if attempt < retries - 1:
                            print(f"Retry {attempt + 1}/{retries} after error: {e}")
                            time.sleep(2 ** attempt)  # Exponential backoff
                        else:
                            raise
                
                # Rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Error generating embeddings for batch {i//batch_size}: {e}")
                # Add zero embeddings for failed batch
                for _ in batch:
                    embeddings.append([0] * 3072)  # Default embedding size
        
        return np.array(embeddings)
    
    def cluster_embeddings(self, embeddings, min_cluster_size=10):
        """Cluster embeddings using HDBSCAN."""
        print("Clustering embeddings...")
        
        # Reduce dimensionality for clustering
        print("Reducing dimensionality with UMAP...")
        reducer = umap.UMAP(n_components=50, random_state=42)
        embeddings_reduced = reducer.fit_transform(embeddings)
        
        # Cluster with HDBSCAN
        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=min_cluster_size,
            min_samples=5,
            metric='euclidean'
        )
        cluster_labels = clusterer.fit_predict(embeddings_reduced)
        
        # Get 2D representation for visualization
        reducer_2d = umap.UMAP(n_components=2, random_state=42)
        embeddings_2d = reducer_2d.fit_transform(embeddings)
        
        print(f"Found {len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0)} clusters")
        return cluster_labels, embeddings_2d
    
    def describe_cluster(self, feedback_samples, cluster_id):
        """Use Gemini LLM to describe a cluster based on sample feedback."""
        # Take up to 20 representative samples
        samples = feedback_samples[:20]
        
        prompt = f"""Analyze the following {len(samples)} feedback comments from documenters. 
These comments are from the same cluster and share similar themes or characteristics.

Feedback samples:
{chr(10).join([f'{i+1}. "{sample}"' for i, sample in enumerate(samples)])}

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
            print(f"Error describing cluster {cluster_id}: {e}")
            return f"Error generating description: {str(e)}"
    
    def analyze_feedback(self, csv_path):
        """Main analysis pipeline."""
        # Load data
        df = self.load_feedback_data(csv_path)
        
        # Generate embeddings
        embeddings = self.generate_embeddings(df['feedback'].tolist())
        
        # Cluster embeddings
        cluster_labels, embeddings_2d = self.cluster_embeddings(embeddings)
        
        # Save embeddings to database
        print("Saving embeddings to database...")
        for idx, row in df.iterrows():
            embedding_json = json.dumps(embeddings[idx].tolist())
            self.cursor.execute("""
                INSERT INTO feedback_embeddings 
                (submission_id, feedback, program_name, assignment_name, created_at, 
                 embedding, cluster_id, reduced_2d_x, reduced_2d_y)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row['submission_id'], row['feedback'], row['program_name'],
                row['assignment_name'], row['created_at'], embedding_json,
                int(cluster_labels[idx]), float(embeddings_2d[idx][0]), 
                float(embeddings_2d[idx][1])
            ))
        
        # Analyze each cluster
        print("Analyzing clusters...")
        unique_clusters = set(cluster_labels)
        if -1 in unique_clusters:
            unique_clusters.remove(-1)  # Remove noise cluster
        
        for cluster_id in tqdm(unique_clusters):
            cluster_mask = cluster_labels == cluster_id
            cluster_feedback = df[cluster_mask]['feedback'].tolist()
            
            # Get cluster description
            description = self.describe_cluster(cluster_feedback, cluster_id)
            
            # Save cluster info
            representative_samples = json.dumps(cluster_feedback[:5])
            self.cursor.execute("""
                INSERT INTO clusters (cluster_id, size, description, representative_samples)
                VALUES (?, ?, ?, ?)
            """, (int(cluster_id), len(cluster_feedback), description, representative_samples))
        
        # Save metadata
        self.cursor.execute("""
            INSERT INTO analysis_metadata (analysis_type, total_samples, num_clusters, parameters)
            VALUES (?, ?, ?, ?)
        """, (
            "feedback_clustering", len(df), len(unique_clusters),
            json.dumps({"min_cluster_size": 10, "embedding_model": EMBEDDING_MODEL})
        ))
        
        self.conn.commit()
        print("Analysis complete!")
    
    def analyze_meeting_types(self):
        """Analyze patterns between meeting types and feedback."""
        print("Analyzing meeting types...")
        
        # Get unique meeting types with sufficient samples
        self.cursor.execute("""
            SELECT assignment_name, COUNT(*) as count
            FROM feedback_embeddings
            WHERE cluster_id >= 0
            GROUP BY assignment_name
            HAVING count > 10
            ORDER BY count DESC
        """)
        meeting_types = self.cursor.fetchall()
        
        for meeting_type, count in tqdm(meeting_types[:50]):  # Top 50 meeting types
            # Get feedback distribution for this meeting type
            self.cursor.execute("""
                SELECT cluster_id, COUNT(*) as count
                FROM feedback_embeddings
                WHERE assignment_name = ? AND cluster_id >= 0
                GROUP BY cluster_id
            """, (meeting_type,))
            
            distribution = dict(self.cursor.fetchall())
            
            # Generate embedding for meeting type name
            try:
                result = self.client.models.embed_content(
                    model=EMBEDDING_MODEL,
                    contents=[meeting_type],
                    config=types.EmbedContentConfig(task_type="CLASSIFICATION")
                )
                meeting_embedding = json.dumps(result.embeddings[0].values)
            except:
                meeting_embedding = json.dumps([0] * 3072)
            
            # Save analysis
            self.cursor.execute("""
                INSERT INTO meeting_type_analysis 
                (meeting_type, embedding, feedback_distribution)
                VALUES (?, ?, ?)
            """, (meeting_type, meeting_embedding, json.dumps(distribution)))
        
        self.conn.commit()
        print("Meeting type analysis complete!")
    
    def close(self):
        """Close database connection."""
        self.conn.close()

def main():
    """Run the analysis."""
    analyzer = FeedbackAnalyzer(GEMINI_API_KEY)
    
    try:
        # Analyze feedback
        analyzer.analyze_feedback("feedback_data.csv")
        
        # Analyze meeting types
        analyzer.analyze_meeting_types()
        
    finally:
        analyzer.close()

if __name__ == "__main__":
    main()