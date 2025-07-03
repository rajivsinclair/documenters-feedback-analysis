#!/usr/bin/env python3
"""
Generate comprehensive visualizations and report from clustered feedback data.
"""

import sqlite3
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from collections import Counter
import os
from datetime import datetime

def load_clustered_data():
    """Load the clustered data from SQLite database."""
    conn = sqlite3.connect('feedback_analysis.db')
    
    # Load feedback with cluster assignments and embeddings
    query = """
    SELECT 
        id,
        submission_id,
        feedback as issue_text,
        program_name as program,
        assignment_name,
        created_at as submission_date,
        cluster_id,
        reduced_2d_x as embedding_2d_x,
        reduced_2d_y as embedding_2d_y
    FROM feedback_embeddings
    WHERE cluster_id IS NOT NULL
    """
    
    df = pd.read_sql_query(query, conn)
    
    # Also load cluster information
    cluster_query = "SELECT * FROM clusters"
    clusters_df = pd.read_sql_query(cluster_query, conn)
    
    conn.close()
    
    # Add placeholder for missing fields
    df['what_was_hard'] = df['issue_text']  # Use issue_text as what_was_hard since it's not separate
    df['additional_info'] = ''  # No additional info in this schema
    
    return df

def create_scatter_plot(df):
    """Create an interactive scatter plot of all entries colored by cluster."""
    # Create hover text with relevant information
    df['hover_text'] = df.apply(lambda row: f"""
    <b>Cluster {row['cluster_id']}</b><br>
    <b>Program:</b> {row['program']}<br>
    <b>Issue:</b> {row['issue_text'][:100]}{'...' if len(str(row['issue_text'])) > 100 else ''}<br>
    <b>What was hard:</b> {str(row['what_was_hard'])[:100]}{'...' if len(str(row['what_was_hard'])) > 100 else ''}<br>
    <b>Date:</b> {row['submission_date']}
    """, axis=1)
    
    # Create the scatter plot
    fig = px.scatter(
        df, 
        x='embedding_2d_x', 
        y='embedding_2d_y',
        color='cluster_id',
        hover_data=['hover_text'],
        title='Full Feedback Dataset: 4,926 Entries Clustered by Similarity',
        labels={
            'embedding_2d_x': 'UMAP Dimension 1',
            'embedding_2d_y': 'UMAP Dimension 2',
            'cluster_id': 'Cluster'
        },
        color_continuous_scale='viridis'
    )
    
    # Update layout
    fig.update_traces(
        hovertemplate='%{customdata[0]}<extra></extra>',
        marker=dict(size=5, opacity=0.7)
    )
    
    fig.update_layout(
        width=1200,
        height=800,
        template='plotly_white',
        font=dict(size=12),
        title_font_size=18,
        showlegend=True
    )
    
    return fig

def create_cluster_size_chart(df):
    """Create a bar chart showing cluster size distribution."""
    cluster_sizes = df['cluster_id'].value_counts().sort_index()
    
    fig = go.Figure(data=[
        go.Bar(
            x=[f'Cluster {i}' for i in cluster_sizes.index],
            y=cluster_sizes.values,
            text=cluster_sizes.values,
            textposition='auto',
            marker_color=['#1f77b4', '#ff7f0e']  # Different colors for each cluster
        )
    ])
    
    fig.update_layout(
        title='Cluster Size Distribution',
        xaxis_title='Cluster',
        yaxis_title='Number of Entries',
        template='plotly_white',
        width=800,
        height=500,
        showlegend=False
    )
    
    # Add annotations for percentages
    total = len(df)
    for i, (cluster_id, count) in enumerate(cluster_sizes.items()):
        percentage = (count / total) * 100
        fig.add_annotation(
            x=f'Cluster {cluster_id}',
            y=count + 50,
            text=f'{percentage:.1f}%',
            showarrow=False,
            font=dict(size=14, color='black')
        )
    
    return fig

def analyze_clusters(df):
    """Analyze each cluster to understand its characteristics."""
    clusters_info = []
    
    for cluster_id in sorted(df['cluster_id'].unique()):
        cluster_df = df[df['cluster_id'] == cluster_id]
        
        # Program distribution
        program_dist = cluster_df['program'].value_counts()
        
        # Sample entries
        sample_entries = cluster_df.sample(min(5, len(cluster_df)))[['issue_text', 'what_was_hard', 'program']]
        
        # Date range
        date_range = f"{cluster_df['submission_date'].min()} to {cluster_df['submission_date'].max()}"
        
        clusters_info.append({
            'cluster_id': cluster_id,
            'size': len(cluster_df),
            'percentage': (len(cluster_df) / len(df)) * 100,
            'program_distribution': program_dist.to_dict(),
            'date_range': date_range,
            'sample_entries': sample_entries
        })
    
    return clusters_info

def generate_markdown_report(df, clusters_info):
    """Generate a comprehensive markdown report."""
    report = f"""# Documentation Feedback Clustering Analysis Report

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary

This report presents the results of clustering analysis performed on **{len(df):,} documentation feedback entries** collected from various programs. The analysis used advanced natural language processing techniques to identify patterns and group similar feedback together.

## Dataset Overview

- **Total Entries:** {len(df):,}
- **Number of Clusters:** {df['cluster_id'].nunique()}
- **Date Range:** {df['submission_date'].min()} to {df['submission_date'].max()}
- **Programs Represented:** {df['program'].nunique()}

## Clustering Results

The clustering algorithm identified **{df['cluster_id'].nunique()} distinct clusters** in the feedback data:

"""
    
    # Add detailed information for each cluster
    for info in clusters_info:
        report += f"""
### Cluster {info['cluster_id']}

- **Size:** {info['size']:,} entries ({info['percentage']:.1f}% of total)
- **Date Range:** {info['date_range']}

#### Program Distribution in Cluster {info['cluster_id']}

| Program | Count | Percentage |
|---------|-------|------------|
"""
        total_in_cluster = info['size']
        for program, count in sorted(info['program_distribution'].items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_in_cluster) * 100
            report += f"| {program} | {count} | {percentage:.1f}% |\n"
        
        report += f"\n#### Sample Entries from Cluster {info['cluster_id']}\n\n"
        
        for idx, row in info['sample_entries'].iterrows():
            report += f"**Entry {idx}** (Program: {row['program']})\n"
            report += f"- **Issue:** {row['issue_text']}\n"
            if pd.notna(row['what_was_hard']):
                report += f"- **What was hard:** {row['what_was_hard']}\n"
            report += "\n"
    
    # Add analysis section
    report += """
## Key Findings

### Cluster Characteristics

"""
    
    if len(clusters_info) == 2 and clusters_info[0]['size'] > 4000:
        report += """
1. **Major Cluster (Cluster 0):** Contains the vast majority of feedback ({:.1f}% of all entries). This suggests that most documentation issues share common themes or characteristics.

2. **Minor Cluster (Cluster 1):** A small cluster with only {} entries ({:.1f}% of total). These entries likely represent outliers or unique types of feedback that differ significantly from the main body of responses.

### Implications

The presence of one dominant cluster suggests:
- Most users experience similar types of documentation challenges
- There may be systematic issues that affect the majority of users
- The small cluster may contain edge cases or specialized feedback worth individual attention

""".format(
            clusters_info[0]['percentage'],
            clusters_info[1]['size'],
            clusters_info[1]['percentage']
        )
    
    # Add methodology section
    report += """
## Methodology

1. **Text Preprocessing:** Feedback text was cleaned and normalized
2. **Embedding Generation:** Used sentence-transformers to create semantic embeddings
3. **Dimensionality Reduction:** Applied UMAP to reduce embeddings to 2D for visualization
4. **Clustering:** Used HDBSCAN algorithm to identify natural clusters in the data
5. **Visualization:** Created interactive plots using Plotly for exploration

## Next Steps

1. **Deep Dive Analysis:** Examine the content of each cluster to identify specific themes
2. **Outlier Investigation:** Analyze the small cluster to understand what makes these entries unique
3. **Action Items:** Develop targeted improvements based on the major themes identified
4. **Continuous Monitoring:** Set up regular clustering analysis to track changes over time

---

*This report was automatically generated from the documentation feedback clustering analysis.*
"""
    
    return report

def main():
    """Main function to generate all visualizations and reports."""
    print("Loading clustered data from database...")
    df = load_clustered_data()
    print(f"Loaded {len(df)} entries")
    
    # Create output directory
    os.makedirs('visualization_output', exist_ok=True)
    
    # Generate scatter plot
    print("Creating scatter plot visualization...")
    scatter_fig = create_scatter_plot(df)
    scatter_fig.write_html('visualization_output/full_cluster_scatter.html')
    print("Saved: visualization_output/full_cluster_scatter.html")
    
    # Generate cluster size chart
    print("Creating cluster size distribution chart...")
    size_fig = create_cluster_size_chart(df)
    size_fig.write_html('visualization_output/full_cluster_sizes.html')
    print("Saved: visualization_output/full_cluster_sizes.html")
    
    # Analyze clusters
    print("Analyzing cluster characteristics...")
    clusters_info = analyze_clusters(df)
    
    # Generate markdown report
    print("Generating comprehensive report...")
    report = generate_markdown_report(df, clusters_info)
    with open('visualization_output/full_cluster_report.md', 'w') as f:
        f.write(report)
    print("Saved: visualization_output/full_cluster_report.md")
    
    # Print summary
    print("\n" + "="*50)
    print("VISUALIZATION GENERATION COMPLETE")
    print("="*50)
    print(f"Total entries visualized: {len(df):,}")
    print(f"Number of clusters: {df['cluster_id'].nunique()}")
    for cluster_id in sorted(df['cluster_id'].unique()):
        cluster_size = len(df[df['cluster_id'] == cluster_id])
        percentage = (cluster_size / len(df)) * 100
        print(f"  - Cluster {cluster_id}: {cluster_size:,} entries ({percentage:.1f}%)")
    print("\nGenerated files:")
    print("  - visualization_output/full_cluster_scatter.html")
    print("  - visualization_output/full_cluster_sizes.html")
    print("  - visualization_output/full_cluster_report.md")

if __name__ == "__main__":
    main()