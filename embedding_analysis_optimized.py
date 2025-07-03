#!/usr/bin/env python3
"""
Optimized Feedback Embedding Analysis
Processes all feedback entries efficiently within API rate limits
"""

import pandas as pd
import numpy as np
import sqlite3
import json
import time
import os
from datetime import datetime, timedelta
from typing import List, Tuple, Optional
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import pickle

from google import genai
from google.genai import types
import umap
import hdbscan
import plotly.express as px
import plotly.graph_objects as go
from tqdm import tqdm

# Configuration
GEMINI_API_KEY = "AIzaSyB5lnc9aQzazfkDETcyai2OoLnUci0SOGU"
EMBEDDING_MODEL = "text-embedding-004"  # Using available model
GENERATION_MODEL = "gemini-2.0-flash"
DB_PATH = "feedback_analysis.db"
CHECKPOINT_PATH = "analysis_checkpoint.pkl"

# Rate limiting configuration
MAX_REQUESTS_PER_SECOND = 20  # 1,200 per minute (80% of 1,500 limit)
BATCH_SIZE = 100  # Optimal batch size for embeddings
CHECKPOINT_INTERVAL = 10  # Save progress every 10 batches

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('analysis.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RateLimiter:
    """Thread-safe rate limiter."""
    def __init__(self, max_per_second):
        self.max_per_second = max_per_second
        self.min_interval = 1.0 / max_per_second
        self.last_request = 0
        self.lock = threading.Lock()
    
    def wait_if_needed(self):
        """Wait if necessary to respect rate limit."""
        with self.lock:
            now = time.time()
            time_since_last = now - self.last_request
            if time_since_last < self.min_interval:
                time.sleep(self.min_interval - time_since_last)
            self.last_request = time.time()

class OptimizedFeedbackAnalyzer:
    def __init__(self, api_key):
        """Initialize the analyzer with optimized settings."""
        self.client = genai.Client(api_key=api_key)
        self.rate_limiter = RateLimiter(MAX_REQUESTS_PER_SECOND)
        self.setup_database()
        self.load_checkpoint()
        
    def setup_database(self):
        """Create SQLite database tables with indexes."""
        self.conn = sqlite3.connect(DB_PATH)
        self.cursor = self.conn.cursor()
        
        # Create tables with optimized schema
        self.cursor.executescript("""
            CREATE TABLE IF NOT EXISTS feedback_embeddings (
                id INTEGER PRIMARY KEY,
                submission_id INTEGER UNIQUE,
                feedback TEXT,
                program_name TEXT,
                assignment_name TEXT,
                created_at TIMESTAMP,
                embedding TEXT,
                cluster_id INTEGER DEFAULT -2,
                reduced_2d_x REAL,
                reduced_2d_y REAL,
                processing_status TEXT DEFAULT 'pending',
                error_message TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS idx_submission_id ON feedback_embeddings(submission_id);
            CREATE INDEX IF NOT EXISTS idx_cluster_id ON feedback_embeddings(cluster_id);
            CREATE INDEX IF NOT EXISTS idx_status ON feedback_embeddings(processing_status);
            
            CREATE TABLE IF NOT EXISTS clusters (
                cluster_id INTEGER PRIMARY KEY,
                size INTEGER,
                description TEXT,
                representative_samples TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS analysis_metadata (
                id INTEGER PRIMARY KEY,
                analysis_phase TEXT,
                total_samples INTEGER,
                processed_samples INTEGER,
                failed_samples INTEGER,
                num_clusters INTEGER,
                parameters TEXT,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS batch_progress (
                batch_id INTEGER PRIMARY KEY,
                start_idx INTEGER,
                end_idx INTEGER,
                status TEXT,
                error_count INTEGER DEFAULT 0,
                processing_time REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        self.conn.commit()
    
    def load_checkpoint(self):
        """Load checkpoint if exists."""
        self.checkpoint = {
            'last_processed_idx': 0,
            'failed_indices': set(),
            'batch_times': []
        }
        
        if os.path.exists(CHECKPOINT_PATH):
            try:
                with open(CHECKPOINT_PATH, 'rb') as f:
                    self.checkpoint = pickle.load(f)
                logger.info(f"Loaded checkpoint: {self.checkpoint['last_processed_idx']} processed")
            except Exception as e:
                logger.warning(f"Could not load checkpoint: {e}")
    
    def save_checkpoint(self):
        """Save current progress."""
        with open(CHECKPOINT_PATH, 'wb') as f:
            pickle.dump(self.checkpoint, f)
    
    def load_feedback_data(self, csv_path):
        """Load all feedback data from CSV."""
        logger.info("Loading feedback data...")
        df = pd.read_csv(csv_path)
        # Filter out very short feedback
        df = df[df['feedback'].str.len() > 50].reset_index(drop=True)
        logger.info(f"Loaded {len(df)} feedback entries")
        
        # Check for existing embeddings
        existing = set()
        self.cursor.execute("SELECT submission_id FROM feedback_embeddings WHERE embedding IS NOT NULL")
        existing = {row[0] for row in self.cursor.fetchall()}
        
        if existing:
            logger.info(f"Found {len(existing)} existing embeddings")
            df = df[~df['submission_id'].isin(existing)]
            logger.info(f"Will process {len(df)} new entries")
        
        return df
    
    def generate_embeddings_batch(self, texts: List[str], batch_idx: int) -> Optional[np.ndarray]:
        """Generate embeddings for a batch of texts with error handling."""
        self.rate_limiter.wait_if_needed()
        
        start_time = time.time()
        retry_count = 0
        max_retries = 3
        
        while retry_count < max_retries:
            try:
                result = self.client.models.embed_content(
                    model=EMBEDDING_MODEL,
                    contents=texts,
                    config=types.EmbedContentConfig(
                        task_type="CLUSTERING"
                    )
                )
                
                embeddings = np.array([e.values for e in result.embeddings])
                
                # Record batch success
                batch_time = time.time() - start_time
                self.cursor.execute("""
                    INSERT INTO batch_progress (batch_id, start_idx, end_idx, status, processing_time)
                    VALUES (?, ?, ?, 'completed', ?)
                """, (batch_idx, batch_idx * BATCH_SIZE, (batch_idx + 1) * BATCH_SIZE, batch_time))
                
                return embeddings
                
            except Exception as e:
                retry_count += 1
                logger.warning(f"Batch {batch_idx} attempt {retry_count} failed: {e}")
                
                if retry_count < max_retries:
                    wait_time = 2 ** retry_count  # Exponential backoff
                    time.sleep(wait_time)
                else:
                    # Record batch failure
                    self.cursor.execute("""
                        INSERT INTO batch_progress (batch_id, start_idx, end_idx, status, error_count)
                        VALUES (?, ?, ?, 'failed', ?)
                    """, (batch_idx, batch_idx * BATCH_SIZE, (batch_idx + 1) * BATCH_SIZE, retry_count))
                    return None
    
    def process_embeddings(self, df):
        """Process all embeddings with progress tracking."""
        logger.info("Generating embeddings...")
        
        # Record analysis start
        self.cursor.execute("""
            INSERT INTO analysis_metadata (analysis_phase, total_samples, processed_samples, start_time)
            VALUES ('embedding_generation', ?, 0, ?)
        """, (len(df), datetime.now()))
        metadata_id = self.cursor.lastrowid
        self.conn.commit()
        
        # Process in batches
        all_embeddings = []
        rows_to_insert = []
        
        num_batches = (len(df) + BATCH_SIZE - 1) // BATCH_SIZE
        
        for batch_idx in tqdm(range(num_batches), desc="Generating embeddings"):
            start_idx = batch_idx * BATCH_SIZE
            end_idx = min((batch_idx + 1) * BATCH_SIZE, len(df))
            
            # Skip if already processed
            if start_idx < self.checkpoint['last_processed_idx']:
                continue
            
            batch_df = df.iloc[start_idx:end_idx]
            batch_texts = batch_df['feedback'].tolist()
            
            # Generate embeddings
            embeddings = self.generate_embeddings_batch(batch_texts, batch_idx)
            
            if embeddings is not None:
                all_embeddings.extend(embeddings)
                
                # Prepare rows for batch insert
                for i, (idx, row) in enumerate(batch_df.iterrows()):
                    embedding_json = json.dumps(embeddings[i].tolist())
                    rows_to_insert.append((
                        row['submission_id'], row['feedback'], row['program_name'],
                        row['assignment_name'], row['created_at'], embedding_json,
                        'completed'
                    ))
            else:
                # Mark failed entries
                for idx, row in batch_df.iterrows():
                    rows_to_insert.append((
                        row['submission_id'], row['feedback'], row['program_name'],
                        row['assignment_name'], row['created_at'], None,
                        'failed'
                    ))
                    self.checkpoint['failed_indices'].add(idx)
            
            # Batch insert every 1000 rows
            if len(rows_to_insert) >= 1000:
                self._batch_insert_embeddings(rows_to_insert)
                rows_to_insert = []
            
            # Update checkpoint
            self.checkpoint['last_processed_idx'] = end_idx
            
            # Save checkpoint periodically
            if batch_idx % CHECKPOINT_INTERVAL == 0:
                self.save_checkpoint()
                self.cursor.execute("""
                    UPDATE analysis_metadata 
                    SET processed_samples = ?
                    WHERE id = ?
                """, (end_idx, metadata_id))
                self.conn.commit()
        
        # Insert remaining rows
        if rows_to_insert:
            self._batch_insert_embeddings(rows_to_insert)
        
        # Update metadata
        self.cursor.execute("""
            UPDATE analysis_metadata 
            SET processed_samples = ?, end_time = ?, failed_samples = ?
            WHERE id = ?
        """, (len(df), datetime.now(), len(self.checkpoint['failed_indices']), metadata_id))
        self.conn.commit()
        
        logger.info(f"Embedding generation complete. Failed: {len(self.checkpoint['failed_indices'])}")
        return np.array(all_embeddings)
    
    def _batch_insert_embeddings(self, rows):
        """Efficiently insert multiple embedding rows."""
        self.cursor.executemany("""
            INSERT OR REPLACE INTO feedback_embeddings 
            (submission_id, feedback, program_name, assignment_name, created_at, 
             embedding, processing_status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, rows)
        self.conn.commit()
    
    def cluster_embeddings(self, min_cluster_size=30):
        """Cluster all embeddings efficiently."""
        logger.info("Loading embeddings for clustering...")
        
        # Load all successful embeddings
        self.cursor.execute("""
            SELECT id, embedding 
            FROM feedback_embeddings 
            WHERE embedding IS NOT NULL
            ORDER BY id
        """)
        
        rows = self.cursor.fetchall()
        ids = [row[0] for row in rows]
        embeddings = np.array([json.loads(row[1]) for row in rows])
        
        logger.info(f"Clustering {len(embeddings)} embeddings...")
        
        # Reduce dimensions for clustering
        reducer = umap.UMAP(
            n_components=50,
            n_neighbors=15,
            min_dist=0.1,
            metric='cosine',
            random_state=42,
            low_memory=True  # Optimize for large datasets
        )
        embeddings_reduced = reducer.fit_transform(embeddings)
        
        # Cluster with HDBSCAN
        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=min_cluster_size,
            min_samples=10,
            metric='euclidean',
            cluster_selection_epsilon=0.5,
            prediction_data=True
        )
        cluster_labels = clusterer.fit_predict(embeddings_reduced)
        
        # Create 2D visualization
        logger.info("Creating 2D visualization...")
        reducer_2d = umap.UMAP(
            n_components=2, 
            random_state=42,
            low_memory=True
        )
        embeddings_2d = reducer_2d.fit_transform(embeddings)
        
        # Update database with cluster assignments
        logger.info("Updating cluster assignments...")
        update_data = [
            (int(cluster_labels[i]), float(embeddings_2d[i][0]), 
             float(embeddings_2d[i][1]), ids[i])
            for i in range(len(ids))
        ]
        
        self.cursor.executemany("""
            UPDATE feedback_embeddings 
            SET cluster_id = ?, reduced_2d_x = ?, reduced_2d_y = ?
            WHERE id = ?
        """, update_data)
        self.conn.commit()
        
        # Report cluster statistics
        unique_clusters = np.unique(cluster_labels)
        cluster_counts = {c: np.sum(cluster_labels == c) for c in unique_clusters}
        
        logger.info(f"Found {len(unique_clusters) - (1 if -1 in unique_clusters else 0)} clusters")
        logger.info(f"Noise points: {cluster_counts.get(-1, 0)}")
        
        return cluster_labels, embeddings_2d
    
    def describe_cluster_concurrent(self, cluster_id: int) -> Tuple[int, str]:
        """Describe a single cluster (for concurrent processing)."""
        self.cursor.execute("""
            SELECT feedback 
            FROM feedback_embeddings 
            WHERE cluster_id = ?
            ORDER BY RANDOM()
            LIMIT 10
        """, (cluster_id,))
        
        samples = [row[0] for row in self.cursor.fetchall()]
        
        if not samples:
            return cluster_id, f"Cluster {cluster_id}: No samples found."
        
        prompt = f"""Analyze these feedback comments that share similar themes:

{chr(10).join([f'{i+1}. "{s}"' for i, s in enumerate(samples)])}

Provide:
1. A concise description of the main theme (2-3 sentences)
2. Key topics or concerns mentioned
3. General tone (positive, negative, neutral, mixed)
4. One actionable insight for program improvement"""

        self.rate_limiter.wait_if_needed()
        
        try:
            response = self.client.models.generate_content(
                model=GENERATION_MODEL,
                contents=prompt
            )
            return cluster_id, response.text
        except Exception as e:
            logger.error(f"Error describing cluster {cluster_id}: {e}")
            return cluster_id, f"Cluster {cluster_id}: Description generation failed."
    
    def analyze_clusters(self):
        """Analyze all clusters with concurrent processing."""
        logger.info("Analyzing clusters...")
        
        # Get unique clusters
        self.cursor.execute("""
            SELECT DISTINCT cluster_id, COUNT(*) as size
            FROM feedback_embeddings 
            WHERE cluster_id >= 0
            GROUP BY cluster_id
            ORDER BY size DESC
        """)
        
        clusters = self.cursor.fetchall()
        logger.info(f"Analyzing {len(clusters)} clusters...")
        
        # Process clusters concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_cluster = {
                executor.submit(self.describe_cluster_concurrent, cluster[0]): cluster
                for cluster in clusters
            }
            
            for future in tqdm(as_completed(future_to_cluster), total=len(clusters), desc="Describing clusters"):
                cluster_info = future_to_cluster[future]
                cluster_id = cluster_info[0]
                size = cluster_info[1]
                
                try:
                    _, description = future.result()
                    
                    # Get representative samples
                    self.cursor.execute("""
                        SELECT feedback 
                        FROM feedback_embeddings 
                        WHERE cluster_id = ?
                        LIMIT 3
                    """, (cluster_id,))
                    samples = [row[0] for row in self.cursor.fetchall()]
                    
                    # Save cluster info
                    self.cursor.execute("""
                        INSERT OR REPLACE INTO clusters 
                        (cluster_id, size, description, representative_samples)
                        VALUES (?, ?, ?, ?)
                    """, (cluster_id, size, description, json.dumps(samples)))
                    
                except Exception as e:
                    logger.error(f"Failed to process cluster {cluster_id}: {e}")
        
        self.conn.commit()
        logger.info("Cluster analysis complete!")
    
    def generate_visualizations(self):
        """Generate all visualizations."""
        logger.info("Generating visualizations...")
        
        # Create output directory
        os.makedirs("visualization_output", exist_ok=True)
        
        # Load data for visualization
        df = pd.read_sql_query("""
            SELECT submission_id, feedback, program_name, cluster_id, 
                   reduced_2d_x as x, reduced_2d_y as y
            FROM feedback_embeddings
            WHERE cluster_id >= -1 AND x IS NOT NULL
        """, self.conn)
        
        # Interactive scatter plot
        fig = px.scatter(
            df[df['cluster_id'] >= 0],
            x='x', y='y',
            color='cluster_id',
            hover_data=['feedback', 'program_name'],
            title=f'Feedback Clusters Visualization ({len(df)} entries)',
            labels={'cluster_id': 'Cluster'},
            color_continuous_scale='Viridis'
        )
        
        # Add noise points
        noise_df = df[df['cluster_id'] == -1]
        if len(noise_df) > 0:
            fig.add_scatter(
                x=noise_df['x'], y=noise_df['y'],
                mode='markers',
                marker=dict(color='lightgray', size=4),
                name='Noise',
                hovertext=noise_df['feedback']
            )
        
        fig.update_layout(width=1200, height=800)
        fig.write_html('visualization_output/cluster_scatter.html')
        
        # Cluster size distribution
        cluster_sizes = df[df['cluster_id'] >= 0]['cluster_id'].value_counts().sort_index()
        
        fig_sizes = go.Figure(data=[
            go.Bar(
                x=cluster_sizes.index,
                y=cluster_sizes.values,
                text=cluster_sizes.values,
                textposition='auto',
            )
        ])
        
        fig_sizes.update_layout(
            title=f'Cluster Size Distribution (Total: {len(df)} entries)',
            xaxis_title='Cluster ID',
            yaxis_title='Number of Feedback Entries',
            showlegend=False
        )
        
        fig_sizes.write_html('visualization_output/cluster_sizes.html')
        
        # Generate cluster descriptions markdown
        self._generate_cluster_report()
        
        logger.info("Visualizations complete!")
    
    def _generate_cluster_report(self):
        """Generate detailed cluster report."""
        with open('visualization_output/cluster_report.md', 'w') as f:
            f.write("# Complete Feedback Cluster Analysis Report\n\n")
            
            # Summary statistics
            self.cursor.execute("""
                SELECT 
                    COUNT(DISTINCT cluster_id) as num_clusters,
                    COUNT(*) as total_entries,
                    SUM(CASE WHEN cluster_id = -1 THEN 1 ELSE 0 END) as noise_count
                FROM feedback_embeddings
                WHERE cluster_id >= -1
            """)
            
            stats = self.cursor.fetchone()
            f.write(f"**Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
            f.write(f"## Summary Statistics\n\n")
            f.write(f"- **Total Feedback Entries Analyzed:** {stats[1]:,}\n")
            f.write(f"- **Number of Clusters Found:** {stats[0] - 1}\n")
            f.write(f"- **Noise Points:** {stats[2]:,} ({stats[2]/stats[1]*100:.1f}%)\n\n")
            
            # Detailed cluster information
            f.write("## Detailed Cluster Analysis\n\n")
            
            self.cursor.execute("""
                SELECT c.cluster_id, c.size, c.description, c.representative_samples
                FROM clusters c
                ORDER BY c.size DESC
            """)
            
            for cluster in self.cursor.fetchall():
                f.write(f"### Cluster {cluster[0]} (Size: {cluster[1]:,})\n\n")
                f.write(f"{cluster[2]}\n\n")
                
                samples = json.loads(cluster[3])
                f.write("**Sample Feedback:**\n\n")
                for i, sample in enumerate(samples, 1):
                    f.write(f"{i}. \"{sample[:200]}...\"\n\n")
                
                # Program distribution for this cluster
                self.cursor.execute("""
                    SELECT program_name, COUNT(*) as count
                    FROM feedback_embeddings
                    WHERE cluster_id = ?
                    GROUP BY program_name
                    ORDER BY count DESC
                    LIMIT 5
                """, (cluster[0],))
                
                programs = self.cursor.fetchall()
                if programs:
                    f.write("**Top Programs in this Cluster:**\n")
                    for prog in programs:
                        f.write(f"- {prog[0]}: {prog[1]} entries\n")
                    f.write("\n")
                
                f.write("---\n\n")
    
    def run_full_analysis(self, csv_path):
        """Run the complete analysis pipeline."""
        start_time = time.time()
        
        try:
            # Load data
            df = self.load_feedback_data(csv_path)
            
            if len(df) > 0:
                # Generate embeddings
                self.process_embeddings(df)
            
            # Cluster all embeddings
            self.cluster_embeddings()
            
            # Analyze clusters
            self.analyze_clusters()
            
            # Generate visualizations
            self.generate_visualizations()
            
            # Clean up checkpoint
            if os.path.exists(CHECKPOINT_PATH):
                os.remove(CHECKPOINT_PATH)
            
            total_time = time.time() - start_time
            logger.info(f"Analysis complete! Total time: {total_time/60:.1f} minutes")
            
            # Print summary
            self.cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(DISTINCT cluster_id) - 1 as num_clusters,
                    SUM(CASE WHEN cluster_id = -1 THEN 1 ELSE 0 END) as noise
                FROM feedback_embeddings
                WHERE embedding IS NOT NULL
            """)
            
            stats = self.cursor.fetchone()
            print(f"\n{'='*50}")
            print(f"ANALYSIS COMPLETE!")
            print(f"{'='*50}")
            print(f"Total entries processed: {stats[0]:,}")
            print(f"Clusters found: {stats[1]}")
            print(f"Noise points: {stats[2]:,}")
            print(f"Processing time: {total_time/60:.1f} minutes")
            print(f"\nView results in:")
            print(f"- visualization_output/cluster_scatter.html")
            print(f"- visualization_output/cluster_report.md")
            print(f"{'='*50}\n")
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            raise
        finally:
            self.conn.close()

def main():
    """Run the optimized analysis."""
    analyzer = OptimizedFeedbackAnalyzer(GEMINI_API_KEY)
    analyzer.run_full_analysis('feedback_data.csv')

if __name__ == "__main__":
    main()