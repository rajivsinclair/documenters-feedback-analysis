#!/bin/bash

echo "============================================"
echo "DOCUMENTERS FEEDBACK ANALYSIS - 10 CLUSTERS"
echo "============================================"
echo ""
echo "Opening key deliverables in your browser..."
echo ""

# Get the current directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Open the main dashboard
echo "1. Opening Cluster Dashboard..."
open "$DIR/cluster_dashboard.html"

# Small delay to avoid overwhelming the browser
sleep 1

# Open the styled visualization
echo "2. Opening Interactive Cluster Visualization..."
open "$DIR/visualization_output_refined/cluster_scatter_styled.html"

sleep 1

# Open the cluster sizes chart
echo "3. Opening Cluster Distribution Chart..."
open "$DIR/visualization_output_refined/cluster_sizes_styled.html"

echo ""
echo "Key documents to review:"
echo "- EXECUTIVE_SUMMARY_10_CLUSTERS.md - High-level overview"
echo "- ACTIONABLE_INSIGHTS.md - Implementation roadmap"
echo "- visualization_output_refined/refined_cluster_analysis.md - Detailed analysis"
echo ""
echo "All files are in: $DIR"
echo ""