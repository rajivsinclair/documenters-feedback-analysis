#!/usr/bin/env python3
"""
Create the final, polished visualization with distinct colors and clean design
"""

import pandas as pd
import numpy as np
import sqlite3
import json
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import umap

def load_data():
    """Load embeddings and cluster data."""
    conn = sqlite3.connect("feedback_analysis.db")
    
    query = """
    SELECT id, submission_id, feedback, program_name, embedding, cluster_id
    FROM feedback_embeddings 
    WHERE embedding IS NOT NULL AND cluster_id >= 0
    """
    
    df = pd.read_sql_query(query, conn)
    embeddings = np.array([json.loads(emb) for emb in df['embedding']])
    
    conn.close()
    return df, embeddings

def create_clean_visualization():
    """Create a clean, distinctive visualization."""
    df, embeddings = load_data()
    
    # Create 2D embedding for visualization
    print("Creating 2D visualization...")
    reducer_2d = umap.UMAP(
        n_components=2, 
        random_state=42, 
        min_dist=0.3,
        n_neighbors=30,
        metric='cosine'
    )
    embeddings_2d = reducer_2d.fit_transform(embeddings)
    
    # Add coordinates to dataframe
    df['x'] = embeddings_2d[:, 0]
    df['y'] = embeddings_2d[:, 1]
    
    # Define distinct cluster themes and colors
    cluster_info = {
        0: {
            'name': 'Process & Learning',
            'color': '#E74C3C',  # Red
            'description': 'First-time experiences, learning process, toolkit feedback'
        },
        1: {
            'name': 'Meeting Access Issues', 
            'color': '#3498DB',  # Blue
            'description': 'Audio problems, missing agendas, technical difficulties'
        },
        2: {
            'name': 'Community Engagement',
            'color': '#2ECC71',  # Green  
            'description': 'Public participation, community feedback, civic engagement'
        },
        3: {
            'name': 'Technical Infrastructure',
            'color': '#F39C12',  # Orange
            'description': 'Streaming issues, virtual meeting problems, recording challenges'
        }
    }
    
    # Create the plot
    fig = go.Figure()
    
    for cluster_id in sorted(df['cluster_id'].unique()):
        cluster_data = df[df['cluster_id'] == cluster_id]
        info = cluster_info[cluster_id]
        
        fig.add_trace(go.Scatter(
            x=cluster_data['x'],
            y=cluster_data['y'],
            mode='markers',
            name=f"{info['name']} ({len(cluster_data)})",
            marker=dict(
                color=info['color'],
                size=6,
                opacity=0.7,
                line=dict(width=0.5, color='white')
            ),
            hovertemplate=(
                "<b>%{fullData.name}</b><br>" +
                "Program: %{customdata[0]}<br>" +
                "Feedback: %{customdata[1]}<br>" +
                "<extra></extra>"
            ),
            customdata=[[row['program_name'], row['feedback'][:150] + "..."] 
                       for _, row in cluster_data.iterrows()]
        ))
    
    # Clean layout - NO AXIS LABELS
    fig.update_layout(
        title={
            'text': f'Documenter Feedback Themes ({len(df):,} entries)',
            'x': 0.5,
            'font': {'size': 24, 'family': 'system-ui, -apple-system, sans-serif', 'color': '#2c3e50'}
        },
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
            font={'size': 14, 'family': 'system-ui, -apple-system, sans-serif'},
            bgcolor='rgba(255,255,255,0.8)',
            bordercolor='#E8E8E8',
            borderwidth=1
        ),
        width=1000,
        height=600,
        plot_bgcolor='#FEFEFE',
        paper_bgcolor='white',
        margin=dict(l=20, r=150, t=60, b=20)
    )
    
    # Remove ALL axis elements
    fig.update_xaxes(
        showticklabels=False,
        showgrid=False,
        zeroline=False,
        visible=False,
        title=""
    )
    fig.update_yaxes(
        showticklabels=False,
        showgrid=False,
        zeroline=False,
        visible=False,
        title=""
    )
    
    return fig, cluster_info

def main():
    """Create the final visualization."""
    print("Creating final visualization...")
    fig, cluster_info = create_clean_visualization()
    
    # Save visualization
    import os
    os.makedirs("visualization_output", exist_ok=True)
    fig.write_html("visualization_output/final_clusters.html", 
                   config={'displayModeBar': False})
    
    print("✅ Final visualization saved to: visualization_output/final_clusters.html")
    
    # Print cluster info for web page
    print("\n=== CLUSTER INFO FOR WEB PAGE ===")
    for cluster_id, info in cluster_info.items():
        print(f"Cluster {cluster_id}: {info['name']} - {info['description']}")

if __name__ == "__main__":
    main()