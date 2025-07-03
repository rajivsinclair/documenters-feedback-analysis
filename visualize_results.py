#!/usr/bin/env python3
"""
Visualize and export results from the embedding analysis
"""

import sqlite3
import pandas as pd
import numpy as np
import json
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

class ResultsVisualizer:
    def __init__(self, db_path="feedback_analysis_demo.db"):
        """Initialize visualizer with database connection."""
        self.conn = sqlite3.connect(db_path)
        self.output_dir = Path("visualization_output")
        self.output_dir.mkdir(exist_ok=True)
        
    def load_cluster_data(self):
        """Load cluster information from database."""
        query = """
            SELECT c.cluster_id, c.size, c.description, c.representative_samples,
                   COUNT(f.id) as actual_size
            FROM clusters c
            LEFT JOIN feedback_embeddings f ON c.cluster_id = f.cluster_id
            WHERE c.cluster_id >= 0
            GROUP BY c.cluster_id
            ORDER BY actual_size DESC
        """
        return pd.read_sql_query(query, self.conn)
    
    def load_embeddings_2d(self):
        """Load 2D embeddings for visualization."""
        query = """
            SELECT cluster_id, reduced_2d_x, reduced_2d_y, program_name
            FROM feedback_embeddings
            WHERE cluster_id >= 0
        """
        return pd.read_sql_query(query, self.conn)
    
    def create_cluster_scatter(self):
        """Create interactive scatter plot of clusters."""
        df = self.load_embeddings_2d()
        clusters = self.load_cluster_data()
        
        # Create cluster labels
        cluster_labels = {}
        for _, row in clusters.iterrows():
            desc = row['description'].split('.')[0] if row['description'] else f"Cluster {row['cluster_id']}"
            cluster_labels[row['cluster_id']] = f"Cluster {row['cluster_id']}: {desc[:50]}..."
        
        df['cluster_label'] = df['cluster_id'].map(cluster_labels)
        
        # Create scatter plot
        fig = px.scatter(
            df, x='reduced_2d_x', y='reduced_2d_y', 
            color='cluster_label', 
            hover_data=['program_name'],
            title='Documenters Feedback Clusters',
            labels={'reduced_2d_x': 'UMAP Dimension 1', 'reduced_2d_y': 'UMAP Dimension 2'}
        )
        
        fig.update_layout(
            width=1000, height=700,
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=1.01
            )
        )
        
        fig.write_html(self.output_dir / "cluster_scatter.html")
        fig.write_image(self.output_dir / "cluster_scatter.png")
        return fig
    
    def create_cluster_sizes_chart(self):
        """Create bar chart of cluster sizes."""
        clusters = self.load_cluster_data()
        
        fig = px.bar(
            clusters.head(20), 
            x='cluster_id', 
            y='actual_size',
            title='Top 20 Feedback Clusters by Size',
            labels={'actual_size': 'Number of Feedback Entries', 'cluster_id': 'Cluster ID'}
        )
        
        fig.write_html(self.output_dir / "cluster_sizes.html")
        fig.write_image(self.output_dir / "cluster_sizes.png")
        return fig
    
    def create_program_distribution(self):
        """Create visualization of feedback distribution by program."""
        query = """
            SELECT program_name, cluster_id, COUNT(*) as count
            FROM feedback_embeddings
            WHERE cluster_id >= 0
            GROUP BY program_name, cluster_id
            ORDER BY count DESC
        """
        df = pd.read_sql_query(query, self.conn)
        
        # Get top programs
        top_programs = df.groupby('program_name')['count'].sum().nlargest(10).index
        df_top = df[df['program_name'].isin(top_programs)]
        
        # Create stacked bar chart
        pivot_df = df_top.pivot(index='program_name', columns='cluster_id', values='count').fillna(0)
        
        fig = go.Figure()
        for cluster_id in pivot_df.columns[:10]:  # Top 10 clusters
            fig.add_trace(go.Bar(
                name=f'Cluster {cluster_id}',
                x=pivot_df.index,
                y=pivot_df[cluster_id]
            ))
        
        fig.update_layout(
            barmode='stack',
            title='Feedback Cluster Distribution by Program (Top 10 Programs)',
            xaxis_title='Program',
            yaxis_title='Number of Feedback Entries',
            width=1000,
            height=600
        )
        
        fig.write_html(self.output_dir / "program_distribution.html")
        fig.write_image(self.output_dir / "program_distribution.png")
        return fig
    
    def export_cluster_descriptions(self):
        """Export cluster descriptions to markdown."""
        clusters = self.load_cluster_data()
        
        md_content = ["# Documenters Feedback Cluster Analysis\n"]
        md_content.append(f"Total clusters identified: {len(clusters)}\n")
        
        for _, cluster in clusters.iterrows():
            md_content.append(f"\n## Cluster {cluster['cluster_id']} (Size: {cluster['actual_size']})\n")
            md_content.append(f"{cluster['description']}\n")
            
            # Add sample feedback
            if cluster['representative_samples']:
                samples = json.loads(cluster['representative_samples'])
                md_content.append("\n**Sample Feedback:**\n")
                for i, sample in enumerate(samples[:3], 1):
                    md_content.append(f"{i}. \"{sample[:200]}...\"\n")
        
        with open(self.output_dir / "cluster_descriptions.md", "w") as f:
            f.write("\n".join(md_content))
    
    def create_meeting_type_analysis(self):
        """Analyze feedback patterns by meeting type."""
        query = """
            SELECT meeting_type, feedback_distribution
            FROM meeting_type_analysis
            WHERE feedback_distribution IS NOT NULL
            LIMIT 20
        """
        df = pd.read_sql_query(query, self.conn)
        
        if df.empty:
            print("No meeting type analysis data available yet.")
            return None
        
        # Parse feedback distributions
        meeting_data = []
        for _, row in df.iterrows():
            dist = json.loads(row['feedback_distribution'])
            for cluster_id, count in dist.items():
                meeting_data.append({
                    'meeting_type': row['meeting_type'][:40] + '...',
                    'cluster_id': int(cluster_id),
                    'count': count
                })
        
        meeting_df = pd.DataFrame(meeting_data)
        
        # Create heatmap data
        pivot_df = meeting_df.pivot(index='meeting_type', columns='cluster_id', values='count').fillna(0)
        
        # Normalize by row to show proportions
        pivot_df_norm = pivot_df.div(pivot_df.sum(axis=1), axis=0)
        
        fig = px.imshow(
            pivot_df_norm.values,
            labels=dict(x="Cluster ID", y="Meeting Type", color="Proportion"),
            x=[f"C{i}" for i in pivot_df_norm.columns],
            y=pivot_df_norm.index,
            title="Feedback Pattern Distribution by Meeting Type",
            aspect="auto",
            color_continuous_scale="Viridis"
        )
        
        fig.update_layout(width=1000, height=800)
        fig.write_html(self.output_dir / "meeting_type_patterns.html")
        fig.write_image(self.output_dir / "meeting_type_patterns.png")
        return fig
    
    def generate_summary_stats(self):
        """Generate summary statistics."""
        stats = {}
        
        # Total feedback analyzed
        stats['total_feedback'] = self.conn.execute(
            "SELECT COUNT(*) FROM feedback_embeddings"
        ).fetchone()[0]
        
        # Number of clusters
        stats['num_clusters'] = self.conn.execute(
            "SELECT COUNT(DISTINCT cluster_id) FROM feedback_embeddings WHERE cluster_id >= 0"
        ).fetchone()[0]
        
        # Programs analyzed
        stats['num_programs'] = self.conn.execute(
            "SELECT COUNT(DISTINCT program_name) FROM feedback_embeddings"
        ).fetchone()[0]
        
        # Meeting types analyzed
        stats['num_meeting_types'] = self.conn.execute(
            "SELECT COUNT(DISTINCT assignment_name) FROM feedback_embeddings"
        ).fetchone()[0]
        
        # Average cluster size
        stats['avg_cluster_size'] = self.conn.execute(
            "SELECT AVG(cnt) FROM (SELECT COUNT(*) as cnt FROM feedback_embeddings WHERE cluster_id >= 0 GROUP BY cluster_id)"
        ).fetchone()[0]
        
        # Save stats
        with open(self.output_dir / "summary_stats.json", "w") as f:
            json.dump(stats, f, indent=2)
        
        return stats
    
    def run_all_visualizations(self):
        """Run all visualization methods."""
        print("Creating cluster scatter plot...")
        self.create_cluster_scatter()
        
        print("Creating cluster sizes chart...")
        self.create_cluster_sizes_chart()
        
        print("Creating program distribution chart...")
        self.create_program_distribution()
        
        print("Exporting cluster descriptions...")
        self.export_cluster_descriptions()
        
        print("Creating meeting type analysis...")
        self.create_meeting_type_analysis()
        
        print("Generating summary statistics...")
        stats = self.generate_summary_stats()
        
        print("\nSummary Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        print(f"\nAll visualizations saved to {self.output_dir}/")
    
    def close(self):
        """Close database connection."""
        self.conn.close()

def main():
    """Run visualization pipeline."""
    visualizer = ResultsVisualizer()
    try:
        visualizer.run_all_visualizations()
    finally:
        visualizer.close()

if __name__ == "__main__":
    main()