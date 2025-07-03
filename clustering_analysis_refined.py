#!/usr/bin/env python3
"""
Refined clustering analysis to find 5-10 meaningful clusters
Excludes Twitter thread links and adjusts parameters
"""

import pandas as pd
import numpy as np
import sqlite3
import json
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import umap
import hdbscan
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from datetime import datetime
from google import genai
from google.genai import types
import time

# Configuration
GEMINI_API_KEY = "AIzaSyB5lnc9aQzazfkDETcyai2OoLnUci0SOGU"
DB_PATH = "feedback_analysis.db"
OUTPUT_DIR = "visualization_output_refined"

# Create output directory
os.makedirs(OUTPUT_DIR, exist_ok=True)

class RefinedClusterAnalyzer:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        
    def load_and_filter_data(self):
        """Load embeddings and filter out Twitter links."""
        print("Loading data and filtering Twitter links...")
        
        # Load all data with embeddings
        query = """
        SELECT id, submission_id, feedback, program_name, assignment_name, 
               embedding, created_at
        FROM feedback_embeddings
        WHERE embedding IS NOT NULL
        AND feedback NOT LIKE '%twitter.com%'
        AND feedback NOT LIKE '%Thread Link%'
        AND LENGTH(feedback) > 100
        """
        
        df = pd.read_sql_query(query, self.conn)
        print(f"Loaded {len(df)} non-Twitter feedback entries")
        
        # Parse embeddings
        embeddings = np.array([json.loads(emb) for emb in df['embedding'].values])
        
        return df, embeddings
    
    def find_optimal_clusters(self, embeddings, min_k=5, max_k=10):
        """Find optimal number of clusters using multiple methods."""
        print(f"\nFinding optimal clusters between {min_k} and {max_k}...")
        
        # First reduce dimensions for clustering
        print("Reducing dimensions with UMAP...")
        reducer = umap.UMAP(
            n_components=50,
            n_neighbors=30,
            min_dist=0.1,
            metric='cosine',
            random_state=42
        )
        embeddings_reduced = reducer.fit_transform(embeddings)
        
        # Try different clustering approaches
        results = {}
        
        # 1. HDBSCAN with different min_cluster_sizes
        print("\nTrying HDBSCAN with various parameters...")
        for min_size in [50, 100, 150, 200, 250, 300]:
            clusterer = hdbscan.HDBSCAN(
                min_cluster_size=min_size,
                min_samples=25,
                cluster_selection_epsilon=0.3,
                metric='euclidean',
                cluster_selection_method='eom'
            )
            labels = clusterer.fit_predict(embeddings_reduced)
            n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
            noise_ratio = (labels == -1).sum() / len(labels)
            
            if min_k <= n_clusters <= max_k and noise_ratio < 0.3:
                results[f'hdbscan_{min_size}'] = {
                    'labels': labels,
                    'n_clusters': n_clusters,
                    'noise_ratio': noise_ratio,
                    'method': f'HDBSCAN(min_size={min_size})'
                }
                print(f"  min_size={min_size}: {n_clusters} clusters, {noise_ratio:.1%} noise")
        
        # 2. K-Means with silhouette score
        print("\nTrying K-Means clustering...")
        silhouette_scores = {}
        for k in range(min_k, max_k + 1):
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = kmeans.fit_predict(embeddings_reduced)
            score = silhouette_score(embeddings_reduced, labels)
            silhouette_scores[k] = score
            
            results[f'kmeans_{k}'] = {
                'labels': labels,
                'n_clusters': k,
                'noise_ratio': 0,
                'silhouette_score': score,
                'method': f'K-Means(k={k})'
            }
            print(f"  k={k}: silhouette score = {score:.3f}")
        
        # Select best result
        best_method = None
        best_score = -1
        
        for method, result in results.items():
            if 'silhouette_score' in result:
                score = result['silhouette_score']
            else:
                # For HDBSCAN, use a composite score
                score = (1 - result['noise_ratio']) * 0.5 + (result['n_clusters'] / max_k) * 0.5
            
            if score > best_score and min_k <= result['n_clusters'] <= max_k:
                best_score = score
                best_method = method
        
        print(f"\nBest method: {results[best_method]['method']}")
        return results[best_method]['labels'], embeddings_reduced
    
    def create_2d_visualization(self, embeddings_reduced, labels):
        """Create 2D visualization of clusters."""
        print("\nCreating 2D visualization...")
        
        # Reduce to 2D for visualization
        reducer_2d = umap.UMAP(
            n_components=2,
            n_neighbors=30,
            min_dist=0.1,
            random_state=42
        )
        embeddings_2d = reducer_2d.fit_transform(embeddings_reduced)
        
        return embeddings_2d
    
    def describe_clusters(self, df, labels):
        """Generate AI descriptions for each cluster."""
        print("\nGenerating cluster descriptions...")
        
        unique_labels = sorted(set(labels))
        if -1 in unique_labels:
            unique_labels.remove(-1)
        
        cluster_descriptions = {}
        
        for label in unique_labels:
            print(f"  Analyzing cluster {label}...")
            cluster_mask = labels == label
            cluster_df = df[cluster_mask]
            
            # Sample up to 20 diverse entries
            if len(cluster_df) > 20:
                sample_df = cluster_df.sample(n=20, random_state=42)
            else:
                sample_df = cluster_df
            
            # Create prompt
            feedback_samples = sample_df['feedback'].tolist()
            prompt = f"""Analyze these {len(cluster_df)} feedback entries (showing {len(feedback_samples)} samples) that were grouped together by AI clustering:

{chr(10).join([f'{i+1}. "{fb[:300]}..."' if len(fb) > 300 else f'{i+1}. "{fb}"' for i, fb in enumerate(feedback_samples)])}

Provide a comprehensive analysis:

1. **Main Theme**: What is the primary common theme connecting these feedback entries? (2-3 sentences)

2. **Key Topics**: List 3-5 specific topics or issues mentioned frequently

3. **Tone Analysis**: What is the overall tone? (positive/negative/neutral/mixed) and why?

4. **Common Challenges**: What specific problems do documenters face in this cluster?

5. **Distinguishing Features**: What makes this cluster different from other feedback?

6. **Actionable Insights**: Provide 2-3 specific recommendations to address these issues

7. **Cluster Name**: Suggest a short, descriptive name for this cluster (3-5 words)"""

            try:
                response = self.client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt
                )
                
                cluster_descriptions[label] = {
                    'size': len(cluster_df),
                    'description': response.text,
                    'samples': feedback_samples[:5],
                    'programs': cluster_df['program_name'].value_counts().to_dict()
                }
                
                time.sleep(2)  # Rate limiting
                
            except Exception as e:
                print(f"    Error describing cluster {label}: {e}")
                cluster_descriptions[label] = {
                    'size': len(cluster_df),
                    'description': f"Error generating description: {str(e)}",
                    'samples': feedback_samples[:5],
                    'programs': cluster_df['program_name'].value_counts().to_dict()
                }
        
        return cluster_descriptions
    
    def generate_visualizations(self, df, labels, embeddings_2d, cluster_descriptions):
        """Generate all visualizations."""
        print("\nGenerating visualizations...")
        
        # Add cluster labels to dataframe
        df['cluster'] = labels
        df['x'] = embeddings_2d[:, 0]
        df['y'] = embeddings_2d[:, 1]
        
        # 1. Interactive scatter plot
        fig = px.scatter(
            df[df['cluster'] >= 0],
            x='x', y='y',
            color='cluster',
            hover_data={
                'feedback': True,
                'program_name': True,
                'cluster': True,
                'x': False,
                'y': False
            },
            title=f'Refined Feedback Clustering Analysis ({len(df)} entries)',
            labels={'cluster': 'Cluster'},
            color_continuous_scale='Viridis'
        )
        
        # Add noise points if any
        noise_df = df[df['cluster'] == -1]
        if len(noise_df) > 0:
            fig.add_scatter(
                x=noise_df['x'], y=noise_df['y'],
                mode='markers',
                marker=dict(color='lightgray', size=4),
                name='Unclustered',
                hovertext=noise_df['feedback']
            )
        
        fig.update_layout(width=1200, height=800)
        fig.write_html(f'{OUTPUT_DIR}/refined_cluster_scatter.html')
        
        # 2. Cluster size distribution
        cluster_sizes = df[df['cluster'] >= 0]['cluster'].value_counts().sort_index()
        
        fig_sizes = go.Figure(data=[
            go.Bar(
                x=[f'Cluster {i}' for i in cluster_sizes.index],
                y=cluster_sizes.values,
                text=[f'{v}<br>{v/len(df)*100:.1f}%' for v in cluster_sizes.values],
                textposition='auto',
                marker_color=px.colors.qualitative.Set3[:len(cluster_sizes)]
            )
        ])
        
        fig_sizes.update_layout(
            title='Cluster Size Distribution',
            xaxis_title='Cluster',
            yaxis_title='Number of Entries',
            showlegend=False,
            width=800,
            height=500
        )
        
        fig_sizes.write_html(f'{OUTPUT_DIR}/refined_cluster_sizes.html')
        
        # 3. Program distribution by cluster
        program_cluster = pd.crosstab(df['program_name'], df['cluster'])
        program_cluster = program_cluster[program_cluster.columns[program_cluster.columns >= 0]]
        
        fig_programs = px.bar(
            program_cluster.T,
            title='Program Distribution Across Clusters',
            labels={'value': 'Count', 'index': 'Cluster'},
            barmode='group'
        )
        
        fig_programs.update_layout(width=1200, height=600)
        fig_programs.write_html(f'{OUTPUT_DIR}/refined_program_clusters.html')
    
    def generate_report(self, df, labels, cluster_descriptions):
        """Generate comprehensive markdown report."""
        print("\nGenerating detailed report...")
        
        with open(f'{OUTPUT_DIR}/refined_cluster_analysis.md', 'w') as f:
            f.write("# Refined Feedback Clustering Analysis\n\n")
            f.write(f"**Analysis Date**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
            
            # Summary
            n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
            n_noise = (labels == -1).sum()
            
            f.write("## Executive Summary\n\n")
            f.write(f"- **Total Feedback Entries**: {len(df):,}\n")
            f.write(f"- **Twitter Links Excluded**: Yes\n")
            f.write(f"- **Distinct Clusters Found**: {n_clusters}\n")
            f.write(f"- **Unclustered Entries**: {n_noise:,} ({n_noise/len(df)*100:.1f}%)\n\n")
            
            # Cluster details
            f.write("## Detailed Cluster Analysis\n\n")
            
            for label in sorted(cluster_descriptions.keys()):
                desc = cluster_descriptions[label]
                f.write(f"### Cluster {label}: {desc['size']:,} entries ({desc['size']/len(df)*100:.1f}%)\n\n")
                f.write(f"{desc['description']}\n\n")
                
                f.write("**Sample Feedback:**\n")
                for i, sample in enumerate(desc['samples'][:3], 1):
                    f.write(f"\n{i}. \"{sample[:200]}...\"\n")
                
                f.write("\n**Top Programs in this Cluster:**\n")
                top_programs = sorted(desc['programs'].items(), key=lambda x: x[1], reverse=True)[:5]
                for prog, count in top_programs:
                    f.write(f"- {prog}: {count} entries\n")
                
                f.write("\n---\n\n")
            
            # Insights
            f.write("## Key Insights\n\n")
            f.write("Based on the clustering analysis, we can identify distinct patterns in documenter feedback:\n\n")
            f.write("1. **Diverse Experience Patterns**: Unlike the initial analysis showing one large cluster, ")
            f.write("refined parameters reveal distinct groups of documenter experiences\n\n")
            f.write("2. **Targeted Interventions**: Each cluster represents a specific set of challenges ")
            f.write("that can be addressed with targeted solutions\n\n")
            f.write("3. **Program-Specific Patterns**: Some clusters may be more prevalent in certain programs, ")
            f.write("suggesting location-specific issues\n\n")
    
    def run_analysis(self):
        """Run the complete refined analysis."""
        # Load and filter data
        df, embeddings = self.load_and_filter_data()
        
        # Find optimal clusters
        labels, embeddings_reduced = self.find_optimal_clusters(embeddings)
        
        # Create 2D visualization
        embeddings_2d = self.create_2d_visualization(embeddings_reduced, labels)
        
        # Describe clusters
        cluster_descriptions = self.describe_clusters(df, labels)
        
        # Generate visualizations
        self.generate_visualizations(df, labels, embeddings_2d, cluster_descriptions)
        
        # Generate report
        self.generate_report(df, labels, cluster_descriptions)
        
        # Save cluster assignments to database
        print("\nSaving refined cluster assignments to database...")
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS refined_clusters (
                submission_id INTEGER PRIMARY KEY,
                cluster_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        for idx, row in df.iterrows():
            cursor.execute("""
                INSERT OR REPLACE INTO refined_clusters (submission_id, cluster_id)
                VALUES (?, ?)
            """, (row['submission_id'], int(labels[idx])))
        
        self.conn.commit()
        
        print(f"\nAnalysis complete! Results saved to {OUTPUT_DIR}/")
        print(f"Found {len(set(labels)) - (1 if -1 in labels else 0)} distinct clusters")

def main():
    analyzer = RefinedClusterAnalyzer()
    analyzer.run_analysis()

if __name__ == "__main__":
    main()