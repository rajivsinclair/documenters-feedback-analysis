#!/usr/bin/env python3
"""
Embedding Analysis for Documenters Feedback - Fixed Version
This script analyzes text feedback using Google Gemini embeddings and clustering.

Key fixes:
1. Removed 'title' parameter from embed_content API calls
2. Fixed SQLite threading issues by creating connections within threads
3. Using INSERT OR REPLACE for batch progress
4. Added validation before clustering
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
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Configuration
GEMINI_API_KEY = "AIzaSyDPNCzGo0LXmSXXobTs45Mrxeq2kCYG_vg"
EMBEDDING_MODEL = "models/text-embedding-004"
LLM_MODEL = "gemini-2.0-flash"
DB_PATH = "feedback_analysis.db"
BATCH_SIZE = 100  # For embedding generation

class FeedbackAnalyzer:
    def __init__(self, api_key):
        """Initialize the analyzer with Gemini API."""
        self.client = genai.Client(api_key=api_key)
        self.api_key = api_key  # Store for thread-local clients
        self.setup_database()
        self._thread_local = threading.local()
        
    def get_thread_connection(self):
        """Get a thread-local database connection."""
        if not hasattr(self._thread_local, 'conn'):
            self._thread_local.conn = sqlite3.connect(DB_PATH)
        return self._thread_local.conn
        
    def setup_database(self):
        """Create SQLite database tables."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create tables
        cursor.executescript("""
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
            
            CREATE TABLE IF NOT EXISTS batch_progress (
                batch_id INTEGER PRIMARY KEY,
                status TEXT,
                total_items INTEGER,
                processed_items INTEGER,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        conn.close()
    
    def load_feedback_data(self, csv_path):
        """Load feedback data from CSV."""
        print("Loading feedback data...")
        df = pd.read_csv(csv_path)
        # Filter out very short feedback
        df = df[df['feedback'].str.len() > 50]
        print(f"Loaded {len(df)} feedback entries")
        return df
    
    def generate_embeddings_batch(self, texts, batch_id=None):
        """Generate embeddings for a batch of texts with proper error handling."""
        embeddings = []
        
        # Create a new connection for this batch
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        if batch_id is not None:
            cursor.execute("""
                INSERT OR REPLACE INTO batch_progress 
                (batch_id, status, total_items, processed_items, updated_at)
                VALUES (?, 'processing', ?, 0, CURRENT_TIMESTAMP)
            """, (batch_id, len(texts)))
            conn.commit()
        
        try:
            # Generate embeddings with retry logic
            retries = 3
            for attempt in range(retries):
                try:
                    # Fixed: Removed title parameter from config
                    result = self.client.models.embed_content(
                        model=EMBEDDING_MODEL,
                        contents=texts,
                        config=types.EmbedContentConfig(
                            task_type="CLUSTERING"
                            # title parameter removed
                        )
                    )
                    
                    for embedding in result.embeddings:
                        embeddings.append(embedding.values)
                    
                    if batch_id is not None:
                        cursor.execute("""
                            INSERT OR REPLACE INTO batch_progress 
                            (batch_id, status, total_items, processed_items, updated_at)
                            VALUES (?, 'completed', ?, ?, CURRENT_TIMESTAMP)
                        """, (batch_id, len(texts), len(texts)))
                        conn.commit()
                    
                    break
                    
                except Exception as e:
                    if attempt < retries - 1:
                        print(f"Retry {attempt + 1}/{retries} after error: {e}")
                        time.sleep(2 ** attempt)  # Exponential backoff
                    else:
                        raise
                        
        except Exception as e:
            print(f"Error generating embeddings for batch: {e}")
            if batch_id is not None:
                cursor.execute("""
                    INSERT OR REPLACE INTO batch_progress 
                    (batch_id, status, total_items, processed_items, error_message, updated_at)
                    VALUES (?, 'failed', ?, 0, ?, CURRENT_TIMESTAMP)
                """, (batch_id, len(texts), str(e)))
                conn.commit()
            
            # Add zero embeddings for failed batch
            for _ in texts:
                embeddings.append([0] * 3072)  # Default embedding size
        
        finally:
            conn.close()
            
        return embeddings
    
    def generate_embeddings(self, texts, batch_size=100):
        """Generate embeddings for a list of texts using Gemini."""
        all_embeddings = []
        
        print(f"Generating embeddings for {len(texts)} texts...")
        for i in tqdm(range(0, len(texts), batch_size)):
            batch = texts[i:i+batch_size]
            batch_id = i // batch_size
            
            embeddings = self.generate_embeddings_batch(batch, batch_id)
            all_embeddings.extend(embeddings)
            
            # Rate limiting
            time.sleep(0.1)
        
        return np.array(all_embeddings)
    
    def validate_embeddings(self, embeddings):
        """Validate embeddings before clustering."""
        if len(embeddings) == 0:
            raise ValueError("No embeddings to cluster")
        
        # Check for all-zero embeddings
        non_zero_count = np.count_nonzero(np.any(embeddings != 0, axis=1))
        if non_zero_count < 10:
            raise ValueError(f"Too few valid embeddings: {non_zero_count}")
        
        print(f"Validated {non_zero_count}/{len(embeddings)} non-zero embeddings")
        return True
    
    def cluster_embeddings(self, embeddings, min_cluster_size=10):
        """Cluster embeddings using HDBSCAN with validation."""
        print("Clustering embeddings...")
        
        # Validate embeddings first
        self.validate_embeddings(embeddings)
        
        # Filter out zero embeddings
        valid_mask = np.any(embeddings != 0, axis=1)
        valid_embeddings = embeddings[valid_mask]
        
        if len(valid_embeddings) < min_cluster_size * 2:
            print(f"Warning: Only {len(valid_embeddings)} valid embeddings, adjusting min_cluster_size")
            min_cluster_size = max(2, len(valid_embeddings) // 10)
        
        # Reduce dimensionality for clustering
        print("Reducing dimensionality with UMAP...")
        reducer = umap.UMAP(n_components=50, random_state=42)
        embeddings_reduced = reducer.fit_transform(valid_embeddings)
        
        # Cluster with HDBSCAN
        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=min_cluster_size,
            min_samples=5,
            metric='euclidean'
        )
        valid_cluster_labels = clusterer.fit_predict(embeddings_reduced)
        
        # Map back to original indices
        cluster_labels = np.full(len(embeddings), -1)
        cluster_labels[valid_mask] = valid_cluster_labels
        
        # Get 2D representation for visualization
        reducer_2d = umap.UMAP(n_components=2, random_state=42)
        embeddings_2d = reducer_2d.fit_transform(embeddings)
        
        print(f"Found {len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0)} clusters")
        return cluster_labels, embeddings_2d
    
    def describe_cluster_concurrent(self, feedback_samples, cluster_id):
        """Use Gemini LLM to describe a cluster with thread-safe connection."""
        # Create a new connection for this thread
        conn = sqlite3.connect(DB_PATH)
        
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
            # Create a new client for this thread if needed
            client = genai.Client(api_key=self.api_key)
            
            response = client.models.generate_content(
                model=LLM_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=500
                )
            )
            description = response.text
        except Exception as e:
            print(f"Error describing cluster {cluster_id}: {e}")
            description = f"Error generating description: {str(e)}"
        finally:
            conn.close()
            
        return cluster_id, description
    
    def analyze_feedback(self, csv_path):
        """Main analysis pipeline with improved error handling."""
        # Load data
        df = self.load_feedback_data(csv_path)
        
        # Check if embeddings already exist
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM feedback_embeddings")
        existing_count = cursor.fetchone()[0]
        
        if existing_count > 0:
            print(f"Found {existing_count} existing embeddings. Clearing old data...")
            cursor.execute("DELETE FROM feedback_embeddings")
            cursor.execute("DELETE FROM clusters")
            cursor.execute("DELETE FROM analysis_metadata")
            conn.commit()
        
        # Generate embeddings
        embeddings = self.generate_embeddings(df['feedback'].tolist())
        
        # Cluster embeddings
        try:
            cluster_labels, embeddings_2d = self.cluster_embeddings(embeddings)
        except ValueError as e:
            print(f"Clustering failed: {e}")
            conn.close()
            return
        
        # Save embeddings to database
        print("Saving embeddings to database...")
        for i, (idx, row) in enumerate(df.iterrows()):
            embedding_json = json.dumps(embeddings[i].tolist())
            cursor.execute("""
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
        conn.commit()
        
        # Analyze each cluster using concurrent processing
        print("Analyzing clusters...")
        unique_clusters = set(cluster_labels)
        if -1 in unique_clusters:
            unique_clusters.remove(-1)  # Remove noise cluster
        
        cluster_data = []
        for cluster_id in unique_clusters:
            cluster_mask = cluster_labels == cluster_id
            cluster_feedback = df[cluster_mask]['feedback'].tolist()
            cluster_data.append((cluster_id, cluster_feedback))
        
        # Process clusters concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_cluster = {
                executor.submit(self.describe_cluster_concurrent, feedback, cid): (cid, feedback)
                for cid, feedback in cluster_data
            }
            
            for future in tqdm(as_completed(future_to_cluster), total=len(future_to_cluster)):
                cluster_id, cluster_feedback = future_to_cluster[future]
                try:
                    _, description = future.result()
                    
                    # Save cluster info
                    representative_samples = json.dumps(cluster_feedback[:5])
                    cursor.execute("""
                        INSERT INTO clusters (cluster_id, size, description, representative_samples)
                        VALUES (?, ?, ?, ?)
                    """, (int(cluster_id), len(cluster_feedback), description, representative_samples))
                    
                except Exception as e:
                    print(f"Error processing cluster {cluster_id}: {e}")
        
        # Save metadata
        cursor.execute("""
            INSERT INTO analysis_metadata (analysis_type, total_samples, num_clusters, parameters)
            VALUES (?, ?, ?, ?)
        """, (
            "feedback_clustering", len(df), len(unique_clusters),
            json.dumps({"min_cluster_size": 10, "embedding_model": EMBEDDING_MODEL})
        ))
        
        conn.commit()
        conn.close()
        print("Analysis complete!")
    
    def analyze_meeting_types(self):
        """Analyze patterns between meeting types and feedback."""
        print("Analyzing meeting types...")
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get unique meeting types with sufficient samples
        cursor.execute("""
            SELECT assignment_name, COUNT(*) as count
            FROM feedback_embeddings
            WHERE cluster_id >= 0
            GROUP BY assignment_name
            HAVING count > 10
            ORDER BY count DESC
        """)
        meeting_types = cursor.fetchall()
        
        for meeting_type, count in tqdm(meeting_types[:50]):  # Top 50 meeting types
            # Get feedback distribution for this meeting type
            cursor.execute("""
                SELECT cluster_id, COUNT(*) as count
                FROM feedback_embeddings
                WHERE assignment_name = ? AND cluster_id >= 0
                GROUP BY cluster_id
            """, (meeting_type,))
            
            distribution = dict(cursor.fetchall())
            
            # Generate embedding for meeting type name
            try:
                result = self.client.models.embed_content(
                    model=EMBEDDING_MODEL,
                    contents=[meeting_type],
                    config=types.EmbedContentConfig(
                        task_type="CLASSIFICATION"
                        # title parameter removed
                    )
                )
                meeting_embedding = json.dumps(result.embeddings[0].values)
            except:
                meeting_embedding = json.dumps([0] * 3072)
            
            # Save analysis
            cursor.execute("""
                INSERT INTO meeting_type_analysis 
                (meeting_type, embedding, feedback_distribution)
                VALUES (?, ?, ?)
            """, (meeting_type, meeting_embedding, json.dumps(distribution)))
        
        conn.commit()
        conn.close()
        print("Meeting type analysis complete!")
    
    def close(self):
        """Close any open connections."""
        # No persistent connection to close in fixed version
        pass

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