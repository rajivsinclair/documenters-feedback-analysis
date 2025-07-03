#!/usr/bin/env python3
"""
Regenerate cluster visualizations with Documenters design system styling.
Uses clean, flat colors and professional formatting.
"""

import sqlite3
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from datetime import datetime
import json

# Documenters Design System Colors
DOCUMENTERS_COLORS = {
    'primary': '#FFE94E',     # Yellow
    'text': '#1A1A1A',        # Near Black
    'accent': '#E9340E',      # Red
    'link': '#3399FF',        # Blue
    'background': '#FFFFFF',  # White
    'light_gray': '#F5F5F5',  # Light gray for backgrounds
    'medium_gray': '#E0E0E0', # Medium gray for borders
    'dark_gray': '#666666'    # Dark gray for secondary text
}

# Define a discrete color palette for 10 clusters
# Using a combination of Documenters colors and complementary colors
CLUSTER_COLORS = [
    '#FFE94E',  # 0: Primary Yellow
    '#E9340E',  # 1: Accent Red
    '#3399FF',  # 2: Link Blue
    '#00B88A',  # 3: Teal
    '#FF6B35',  # 4: Orange
    '#8B5CF6',  # 5: Purple
    '#10B981',  # 6: Emerald
    '#F59E0B',  # 7: Amber
    '#EC4899',  # 8: Pink
    '#6366F1'   # 9: Indigo
]

def load_refined_cluster_data():
    """Load the refined cluster data from the database."""
    conn = sqlite3.connect('feedback_analysis.db')
    
    # Load feedback with refined cluster assignments
    query = """
    SELECT 
        fe.id,
        fe.submission_id,
        fe.feedback as issue_text,
        fe.program_name as program,
        fe.assignment_name,
        fe.created_at as submission_date,
        rc.cluster_id,
        fe.reduced_2d_x as embedding_2d_x,
        fe.reduced_2d_y as embedding_2d_y
    FROM feedback_embeddings fe
    INNER JOIN refined_clusters rc ON fe.submission_id = rc.submission_id
    WHERE rc.cluster_id IS NOT NULL
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    print(f"Loaded {len(df)} entries with refined cluster assignments")
    return df

def create_styled_scatter_plot(df):
    """Create a clean, professional scatter plot with Documenters styling."""
    # Create the figure
    fig = go.Figure()
    
    # Add traces for each cluster
    for cluster_id in sorted(df['cluster_id'].unique()):
        cluster_data = df[df['cluster_id'] == cluster_id]
        
        # Create hover text
        hover_texts = []
        for _, row in cluster_data.iterrows():
            hover_text = f"""<b>Cluster {cluster_id}</b><br>
<b>Program:</b> {row['program']}<br>
<b>Assignment:</b> {row['assignment_name']}<br>
<b>Feedback:</b> {row['issue_text'][:150]}{'...' if len(str(row['issue_text'])) > 150 else ''}<br>
<b>Date:</b> {row['submission_date']}"""
            hover_texts.append(hover_text)
        
        fig.add_trace(go.Scatter(
            x=cluster_data['embedding_2d_x'],
            y=cluster_data['embedding_2d_y'],
            mode='markers',
            name=f'Cluster {cluster_id}',
            marker=dict(
                color=CLUSTER_COLORS[cluster_id],
                size=8,
                opacity=0.7,
                line=dict(width=0)  # No borders for clean look
            ),
            text=hover_texts,
            hovertemplate='%{text}<extra></extra>',
            hoverlabel=dict(
                bgcolor='white',
                bordercolor=DOCUMENTERS_COLORS['medium_gray'],
                font=dict(
                    family='Arial, sans-serif',
                    size=12,
                    color=DOCUMENTERS_COLORS['text']
                )
            )
        ))
    
    # Update layout with Documenters styling
    fig.update_layout(
        title={
            'text': 'Documentation Feedback Clusters<br><span style="font-size:14px; color:#666666;">10 distinct clusters identified from 3,872 feedback entries</span>',
            'font': {
                'family': 'Arial, sans-serif',
                'size': 24,
                'color': DOCUMENTERS_COLORS['text']
            },
            'x': 0.5,
            'xanchor': 'center'
        },
        xaxis=dict(
            title=dict(
                text='Dimension 1',
                font=dict(
                    family='Arial, sans-serif',
                    size=14,
                    color=DOCUMENTERS_COLORS['dark_gray']
                )
            ),
            gridcolor=DOCUMENTERS_COLORS['medium_gray'],
            zeroline=False,
            showline=True,
            linecolor=DOCUMENTERS_COLORS['medium_gray']
        ),
        yaxis=dict(
            title=dict(
                text='Dimension 2',
                font=dict(
                    family='Arial, sans-serif',
                    size=14,
                    color=DOCUMENTERS_COLORS['dark_gray']
                )
            ),
            gridcolor=DOCUMENTERS_COLORS['medium_gray'],
            zeroline=False,
            showline=True,
            linecolor=DOCUMENTERS_COLORS['medium_gray']
        ),
        plot_bgcolor=DOCUMENTERS_COLORS['background'],
        paper_bgcolor=DOCUMENTERS_COLORS['background'],
        font=dict(
            family='Arial, sans-serif',
            size=12,
            color=DOCUMENTERS_COLORS['text']
        ),
        legend=dict(
            title='Clusters',
            orientation='v',
            yanchor='top',
            y=0.99,
            xanchor='left',
            x=1.01,
            bgcolor='rgba(255, 255, 255, 0.9)',
            bordercolor=DOCUMENTERS_COLORS['medium_gray'],
            borderwidth=1
        ),
        width=1200,
        height=800,
        margin=dict(l=80, r=200, t=100, b=80)
    )
    
    return fig

def create_cluster_size_chart(df):
    """Create a clean bar chart showing cluster size distribution."""
    # Calculate cluster sizes and percentages
    cluster_sizes = df['cluster_id'].value_counts().sort_index()
    total_entries = len(df)
    
    # Create figure
    fig = go.Figure()
    
    # Add bars
    fig.add_trace(go.Bar(
        x=[f'Cluster {i}' for i in cluster_sizes.index],
        y=cluster_sizes.values,
        marker=dict(
            color=[CLUSTER_COLORS[i] for i in cluster_sizes.index],
            line=dict(width=0)  # No borders for flat design
        ),
        text=[f'{size}<br>{size/total_entries*100:.1f}%' for size in cluster_sizes.values],
        textposition='outside',
        textfont=dict(
            family='Arial, sans-serif',
            size=14,
            color=DOCUMENTERS_COLORS['text']
        ),
        hovertemplate='<b>%{x}</b><br>Entries: %{y}<br>Percentage: %{text}<extra></extra>'
    ))
    
    # Update layout
    fig.update_layout(
        title={
            'text': 'Cluster Size Distribution<br><span style="font-size:14px; color:#666666;">Number of feedback entries per cluster</span>',
            'font': {
                'family': 'Arial, sans-serif',
                'size': 24,
                'color': DOCUMENTERS_COLORS['text']
            },
            'x': 0.5,
            'xanchor': 'center'
        },
        xaxis=dict(
            title=dict(
                text='',
                font=dict(
                    family='Arial, sans-serif',
                    size=14,
                    color=DOCUMENTERS_COLORS['dark_gray']
                )
            ),
            tickfont=dict(
                family='Arial, sans-serif',
                size=12,
                color=DOCUMENTERS_COLORS['text']
            ),
            gridcolor='rgba(0,0,0,0)',
            showline=True,
            linecolor=DOCUMENTERS_COLORS['medium_gray']
        ),
        yaxis=dict(
            title=dict(
                text='Number of Entries',
                font=dict(
                    family='Arial, sans-serif',
                    size=14,
                    color=DOCUMENTERS_COLORS['dark_gray']
                )
            ),
            gridcolor=DOCUMENTERS_COLORS['light_gray'],
            zeroline=True,
            zerolinecolor=DOCUMENTERS_COLORS['medium_gray'],
            showline=True,
            linecolor=DOCUMENTERS_COLORS['medium_gray']
        ),
        plot_bgcolor=DOCUMENTERS_COLORS['background'],
        paper_bgcolor=DOCUMENTERS_COLORS['background'],
        font=dict(
            family='Arial, sans-serif',
            size=12,
            color=DOCUMENTERS_COLORS['text']
        ),
        showlegend=False,
        width=1000,
        height=600,
        margin=dict(l=80, r=80, t=100, b=80),
        bargap=0.2
    )
    
    # Add a horizontal line for the average
    avg_size = total_entries / len(cluster_sizes)
    fig.add_shape(
        type='line',
        x0=-0.5,
        x1=len(cluster_sizes)-0.5,
        y0=avg_size,
        y1=avg_size,
        line=dict(
            color=DOCUMENTERS_COLORS['accent'],
            width=2,
            dash='dash'
        )
    )
    
    # Add annotation for average line
    fig.add_annotation(
        x=len(cluster_sizes)-1,
        y=avg_size,
        text=f'Average: {avg_size:.0f}',
        showarrow=False,
        yshift=15,
        font=dict(
            family='Arial, sans-serif',
            size=12,
            color=DOCUMENTERS_COLORS['accent']
        ),
        bgcolor='rgba(255, 255, 255, 0.8)',
        bordercolor=DOCUMENTERS_COLORS['accent'],
        borderwidth=1,
        borderpad=4
    )
    
    return fig

def create_cluster_comparison_chart(df):
    """Create a horizontal bar chart comparing cluster characteristics."""
    # Analyze each cluster
    cluster_stats = []
    
    for cluster_id in sorted(df['cluster_id'].unique()):
        cluster_data = df[df['cluster_id'] == cluster_id]
        
        # Calculate statistics
        stats = {
            'cluster_id': cluster_id,
            'size': len(cluster_data),
            'num_programs': cluster_data['program'].nunique(),
            'avg_feedback_length': cluster_data['issue_text'].str.len().mean(),
            'date_span_days': (pd.to_datetime(cluster_data['submission_date'].max()) - 
                              pd.to_datetime(cluster_data['submission_date'].min())).days
        }
        cluster_stats.append(stats)
    
    stats_df = pd.DataFrame(cluster_stats)
    
    # Create subplots
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Cluster Sizes', 'Programs per Cluster', 
                       'Average Feedback Length', 'Time Span (Days)'),
        vertical_spacing=0.15,
        horizontal_spacing=0.12
    )
    
    # Add traces
    metrics = [
        ('size', 'Entries', 1, 1),
        ('num_programs', 'Programs', 1, 2),
        ('avg_feedback_length', 'Characters', 2, 1),
        ('date_span_days', 'Days', 2, 2)
    ]
    
    for metric, label, row, col in metrics:
        fig.add_trace(
            go.Bar(
                y=[f'C{i}' for i in stats_df['cluster_id']],
                x=stats_df[metric],
                orientation='h',
                marker=dict(
                    color=[CLUSTER_COLORS[i] for i in stats_df['cluster_id']],
                    line=dict(width=0)
                ),
                text=[f'{val:.0f}' if metric != 'avg_feedback_length' else f'{val:.0f}' 
                      for val in stats_df[metric]],
                textposition='outside',
                textfont=dict(size=10),
                name=label,
                showlegend=False,
                hovertemplate=f'<b>%{{y}}</b><br>{label}: %{{x:.0f}}<extra></extra>'
            ),
            row=row, col=col
        )
    
    # Update layout
    fig.update_layout(
        title={
            'text': 'Cluster Characteristics Comparison<br><span style="font-size:14px; color:#666666;">Key metrics across all clusters</span>',
            'font': {
                'family': 'Arial, sans-serif',
                'size': 24,
                'color': DOCUMENTERS_COLORS['text']
            },
            'x': 0.5,
            'xanchor': 'center'
        },
        plot_bgcolor=DOCUMENTERS_COLORS['background'],
        paper_bgcolor=DOCUMENTERS_COLORS['background'],
        font=dict(
            family='Arial, sans-serif',
            size=12,
            color=DOCUMENTERS_COLORS['text']
        ),
        showlegend=False,
        width=1200,
        height=800,
        margin=dict(l=80, r=80, t=120, b=80)
    )
    
    # Update all axes
    for i in range(1, 5):
        row = (i-1) // 2 + 1
        col = (i-1) % 2 + 1
        
        fig.update_xaxes(
            gridcolor=DOCUMENTERS_COLORS['light_gray'],
            showline=True,
            linecolor=DOCUMENTERS_COLORS['medium_gray'],
            row=row, col=col
        )
        fig.update_yaxes(
            gridcolor='rgba(0,0,0,0)',
            showline=True,
            linecolor=DOCUMENTERS_COLORS['medium_gray'],
            row=row, col=col
        )
    
    return fig

def generate_summary_stats(df):
    """Generate summary statistics for the dashboard."""
    total_entries = len(df)
    num_clusters = df['cluster_id'].nunique()
    num_programs = df['program'].nunique()
    date_range = f"{df['submission_date'].min()} to {df['submission_date'].max()}"
    
    # Find largest and smallest clusters
    cluster_sizes = df['cluster_id'].value_counts()
    largest_cluster = cluster_sizes.idxmax()
    smallest_cluster = cluster_sizes.idxmin()
    
    summary = {
        'total_entries': total_entries,
        'num_clusters': num_clusters,
        'num_programs': num_programs,
        'date_range': date_range,
        'largest_cluster': {
            'id': int(largest_cluster),
            'size': int(cluster_sizes[largest_cluster]),
            'percentage': float(cluster_sizes[largest_cluster] / total_entries * 100)
        },
        'smallest_cluster': {
            'id': int(smallest_cluster),
            'size': int(cluster_sizes[smallest_cluster]),
            'percentage': float(cluster_sizes[smallest_cluster] / total_entries * 100)
        },
        'generation_time': datetime.now().isoformat()
    }
    
    return summary

def main():
    """Generate all visualizations with Documenters styling."""
    print("Loading refined cluster data...")
    df = load_refined_cluster_data()
    
    # Create output directory
    os.makedirs('visualization_output_refined', exist_ok=True)
    
    # Generate scatter plot
    print("Creating styled scatter plot...")
    scatter_fig = create_styled_scatter_plot(df)
    scatter_fig.write_html('visualization_output_refined/cluster_scatter_styled.html')
    print("✓ Saved: visualization_output_refined/cluster_scatter_styled.html")
    
    # Generate cluster size chart
    print("Creating cluster size distribution chart...")
    size_fig = create_cluster_size_chart(df)
    size_fig.write_html('visualization_output_refined/cluster_sizes_styled.html')
    print("✓ Saved: visualization_output_refined/cluster_sizes_styled.html")
    
    # Generate cluster comparison chart
    print("Creating cluster comparison chart...")
    comparison_fig = create_cluster_comparison_chart(df)
    comparison_fig.write_html('visualization_output_refined/cluster_comparison_styled.html')
    print("✓ Saved: visualization_output_refined/cluster_comparison_styled.html")
    
    # Generate summary statistics
    print("Generating summary statistics...")
    summary_stats = generate_summary_stats(df)
    with open('visualization_output_refined/summary_stats_styled.json', 'w') as f:
        json.dump(summary_stats, f, indent=2)
    print("✓ Saved: visualization_output_refined/summary_stats_styled.json")
    
    # Print summary
    print("\n" + "="*60)
    print("VISUALIZATION UPDATE COMPLETE")
    print("="*60)
    print(f"Total entries visualized: {summary_stats['total_entries']:,}")
    print(f"Number of clusters: {summary_stats['num_clusters']}")
    print(f"Date range: {summary_stats['date_range']}")
    print(f"Largest cluster: Cluster {summary_stats['largest_cluster']['id']} "
          f"({summary_stats['largest_cluster']['size']} entries, "
          f"{summary_stats['largest_cluster']['percentage']:.1f}%)")
    print(f"Smallest cluster: Cluster {summary_stats['smallest_cluster']['id']} "
          f"({summary_stats['smallest_cluster']['size']} entries, "
          f"{summary_stats['smallest_cluster']['percentage']:.1f}%)")
    print("\nGenerated files:")
    print("  - visualization_output_refined/cluster_scatter_styled.html")
    print("  - visualization_output_refined/cluster_sizes_styled.html")
    print("  - visualization_output_refined/cluster_comparison_styled.html")
    print("  - visualization_output_refined/summary_stats_styled.json")
    print("\nAll visualizations use the Documenters design system colors and styling.")

if __name__ == "__main__":
    main()