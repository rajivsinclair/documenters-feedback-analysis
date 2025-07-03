#!/usr/bin/env python3
"""
Improved clustering to get 4-6 truly distinct clusters
"""

import pandas as pd
import numpy as np
import sqlite3
import json
import plotly.express as px
import plotly.graph_objects as go
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import umap
import hdbscan
from google import genai
from google.genai import types
import time

GEMINI_API_KEY = "AIzaSyB5lnc9aQzazfkDETcyai2OoLnUci0SOGU"
GENERATION_MODEL = "gemini-2.0-flash"

def load_embeddings():
    """Load embeddings from the database."""
    conn = sqlite3.connect("feedback_analysis.db")
    
    query = """
    SELECT id, submission_id, feedback, program_name, embedding
    FROM feedback_embeddings 
    WHERE embedding IS NOT NULL
    """
    
    df = pd.read_sql_query(query, conn)
    embeddings = np.array([json.loads(emb) for emb in df['embedding']])
    
    conn.close()
    return df, embeddings

def try_multiple_clustering_approaches(embeddings, min_clusters=4, max_clusters=6):
    """Try different clustering approaches to find the best distinct clusters."""
    
    results = []
    
    # Approach 1: KMeans with different k values
    scaler = StandardScaler()
    embeddings_scaled = scaler.fit_transform(embeddings)
    
    for k in range(min_clusters, max_clusters + 1):
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(embeddings_scaled)
        
        # Calculate cluster balance (avoid having one huge cluster)
        unique_labels, counts = np.unique(labels, return_counts=True)
        balance_score = np.std(counts) / np.mean(counts)  # Lower is more balanced
        
        results.append({
            'method': f'KMeans_k{k}',
            'labels': labels,
            'n_clusters': k,
            'balance_score': balance_score,
            'min_cluster_size': min(counts),
            'max_cluster_size': max(counts)
        })
    
    # Approach 2: HDBSCAN with different parameters
    reducer = umap.UMAP(n_components=50, random_state=42, min_dist=0.0, metric='cosine')
    embeddings_reduced = reducer.fit_transform(embeddings)
    
    for min_size in [100, 200, 300, 400]:
        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=min_size,
            min_samples=50,
            cluster_selection_epsilon=0.1,
            metric='euclidean'
        )
        labels = clusterer.fit_predict(embeddings_reduced)
        
        unique_labels = np.unique(labels)
        n_clusters = len(unique_labels) - (1 if -1 in unique_labels else 0)
        
        if min_clusters <= n_clusters <= max_clusters:
            counts = [np.sum(labels == label) for label in unique_labels if label != -1]
            if counts:
                balance_score = np.std(counts) / np.mean(counts)
                results.append({
                    'method': f'HDBSCAN_min{min_size}',
                    'labels': labels,
                    'n_clusters': n_clusters,
                    'balance_score': balance_score,
                    'min_cluster_size': min(counts) if counts else 0,
                    'max_cluster_size': max(counts) if counts else 0
                })
    
    # Choose best approach (balanced clusters in the right range)
    valid_results = [r for r in results if min_clusters <= r['n_clusters'] <= max_clusters]
    if not valid_results:
        # Fall back to KMeans with 5 clusters if nothing else works
        kmeans = KMeans(n_clusters=5, random_state=42)
        labels = kmeans.fit_predict(embeddings_scaled)
        return labels, 'KMeans_k5_fallback'
    
    # Sort by balance score (prefer more balanced clusters)
    valid_results.sort(key=lambda x: x['balance_score'])
    best = valid_results[0]
    
    print(f"Selected {best['method']} with {best['n_clusters']} clusters")
    print(f"Cluster sizes: min={best['min_cluster_size']}, max={best['max_cluster_size']}")
    print(f"Balance score: {best['balance_score']:.2f}")
    
    return best['labels'], best['method']

def describe_clusters_with_ai(df, labels):
    """Generate AI descriptions for each cluster."""
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    unique_labels = sorted([l for l in np.unique(labels) if l >= 0])
    cluster_descriptions = {}
    
    for cluster_id in unique_labels:
        cluster_mask = labels == cluster_id
        cluster_feedback = df[cluster_mask]['feedback'].tolist()
        
        # Sample 15 diverse examples for analysis
        if len(cluster_feedback) > 15:
            step = len(cluster_feedback) // 15
            samples = cluster_feedback[::step][:15]
        else:
            samples = cluster_feedback
        
        prompt = f"""Analyze these {len(cluster_feedback)} feedback entries from documenters and identify the MAIN DISTINCT THEME that makes this cluster unique:

{chr(10).join([f'{i+1}. "{s[:300]}..."' for i, s in enumerate(samples)])}

Provide:
1. A clear, specific theme title (3-5 words)
2. What makes this cluster DISTINCT from other feedback types
3. 2-3 key characteristics unique to this theme
4. One specific actionable recommendation

Focus on what makes this cluster DIFFERENT, not general documenter issues."""

        try:
            response = client.models.generate_content(
                model=GENERATION_MODEL,
                contents=prompt
            )
            cluster_descriptions[cluster_id] = response.text
            print(f"✓ Described cluster {cluster_id} ({len(cluster_feedback)} entries)")
            time.sleep(1)  # Rate limiting
        except Exception as e:
            print(f"✗ Failed to describe cluster {cluster_id}: {e}")
            cluster_descriptions[cluster_id] = f"Cluster {cluster_id}: {len(cluster_feedback)} entries"
    
    return cluster_descriptions

def create_clean_visualization(df, labels, descriptions):
    """Create a clean visualization without distracting elements."""
    
    # Create 2D embedding for visualization
    reducer_2d = umap.UMAP(n_components=2, random_state=42, min_dist=0.1)
    embeddings_2d = reducer_2d.fit_transform(np.array([json.loads(emb) for emb in df['embedding']]))
    
    # Add coordinates and labels to dataframe
    df_viz = df.copy()
    df_viz['x'] = embeddings_2d[:, 0]
    df_viz['y'] = embeddings_2d[:, 1]
    df_viz['cluster'] = labels
    
    # Filter out noise points
    df_clean = df_viz[df_viz['cluster'] >= 0]
    
    # Create color palette for clusters
    colors = px.colors.qualitative.Set3[:len(np.unique(df_clean['cluster']))]
    
    fig = go.Figure()
    
    for i, cluster_id in enumerate(sorted(df_clean['cluster'].unique())):
        cluster_data = df_clean[df_clean['cluster'] == cluster_id]
        
        # Get cluster title from description
        desc = descriptions.get(cluster_id, f"Cluster {cluster_id}")
        title_line = desc.split('\n')[0] if '\n' in desc else desc[:50]
        cluster_title = title_line.replace('**', '').replace('#', '').strip()
        
        fig.add_trace(go.Scatter(
            x=cluster_data['x'],
            y=cluster_data['y'],
            mode='markers',
            name=f"{cluster_title} ({len(cluster_data)})",
            marker=dict(
                color=colors[i],
                size=8,
                opacity=0.7,
                line=dict(width=1, color='white')
            ),
            hovertemplate=(
                "<b>%{fullData.name}</b><br>" +
                "Program: %{customdata[0]}<br>" +
                "Feedback: %{customdata[1]}<br>" +
                "<extra></extra>"
            ),
            customdata=[[row['program_name'], row['feedback'][:200] + "..."] 
                       for _, row in cluster_data.iterrows()]
        ))
    
    fig.update_layout(
        title={
            'text': f'Distinct Feedback Themes ({len(df_clean)} entries)',
            'x': 0.5,
            'font': {'size': 24, 'family': 'Arial, sans-serif'}
        },
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
            font={'size': 12}
        ),
        width=1200,
        height=700,
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(l=50, r=200, t=80, b=50)
    )
    
    # Remove all axis elements - they're meaningless for embeddings
    fig.update_xaxes(
        showticklabels=False,
        showgrid=False,
        zeroline=False,
        visible=False
    )
    fig.update_yaxes(
        showticklabels=False,
        showgrid=False,
        zeroline=False,
        visible=False
    )
    
    return fig

def main():
    """Run improved clustering analysis."""
    print("Loading embeddings...")
    df, embeddings = load_embeddings()
    print(f"Loaded {len(embeddings)} embeddings")
    
    print("\nTesting different clustering approaches...")
    labels, method = try_multiple_clustering_approaches(embeddings)
    
    # Count clusters
    unique_labels = np.unique(labels)
    n_clusters = len(unique_labels) - (1 if -1 in unique_labels else 0)
    noise_count = np.sum(labels == -1) if -1 in unique_labels else 0
    
    print(f"\nFinal clustering: {n_clusters} clusters, {noise_count} noise points")
    
    # Show cluster sizes
    for label in sorted(unique_labels):
        if label >= 0:
            count = np.sum(labels == label)
            percentage = count / len(labels) * 100
            print(f"Cluster {label}: {count} entries ({percentage:.1f}%)")
    
    print("\nGenerating AI descriptions...")
    descriptions = describe_clusters_with_ai(df, labels)
    
    print("\nCreating visualization...")
    fig = create_clean_visualization(df, labels, descriptions)
    
    # Save visualization
    import os
    os.makedirs("visualization_output", exist_ok=True)
    fig.write_html("visualization_output/distinct_clusters.html")
    
    # Update database with new clusters
    print("\nUpdating database...")
    conn = sqlite3.connect("feedback_analysis.db")
    cursor = conn.cursor()
    
    for i, (_, row) in enumerate(df.iterrows()):
        cursor.execute("""
            UPDATE feedback_embeddings 
            SET cluster_id = ? 
            WHERE id = ?
        """, (int(labels[i]), row['id']))
    
    # Save cluster descriptions
    cursor.execute("DELETE FROM clusters")
    for cluster_id, description in descriptions.items():
        cursor.execute("""
            INSERT INTO clusters (cluster_id, size, description)
            VALUES (?, ?, ?)
        """, (cluster_id, np.sum(labels == cluster_id), description))
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Improved clustering complete!")
    print(f"📊 Found {n_clusters} distinct clusters")
    print(f"📁 Visualization saved to: visualization_output/distinct_clusters.html")
    
    # Print cluster summaries
    print("\n" + "="*60)
    print("CLUSTER SUMMARIES")
    print("="*60)
    for cluster_id in sorted(descriptions.keys()):
        count = np.sum(labels == cluster_id)
        print(f"\nCluster {cluster_id} ({count} entries):")
        print(descriptions[cluster_id][:200] + "...")

if __name__ == "__main__":
    main()