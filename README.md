# Documenters Feedback Analysis

This project analyzes feedback from the Documenters program using AI-powered text embeddings and clustering techniques to identify common themes and actionable insights.

## Project Structure

```
documenters-feedback-analysis/
├── README.md                          # This file
├── GUIDEBOOK.md                       # Comprehensive methodology guide
├── feedback_analysis_tutorial.ipynb   # Interactive Python notebook
├── index.html                         # Static web page with results
├── feedback_data.csv                  # Extracted feedback data (5,330 entries)
├── embedding_analysis_sample.py       # Main analysis script
├── embedding_analysis_demo.py         # Demo version with synthetic embeddings
└── visualization_output/              # Generated visualizations
    ├── cluster_scatter.html           # Interactive cluster visualization
    ├── cluster_sizes.png              # Cluster size distribution
    └── cluster_descriptions.md        # AI-generated cluster descriptions
```

## Key Findings

The analysis identified 6 distinct clusters of feedback:

1. **Contextual Knowledge Needs** (57 entries) - Need for better background information
2. **Audio & Technical Challenges** (27 entries) - Recording and audio quality issues
3. **Meeting Logistics & Changes** (22 entries) - Schedule changes and time overruns
4. **Location & Accessibility** (19 entries) - Parking and venue challenges
5. **Documentation Process** (12 entries) - Best practices and process improvements
6. **Meeting Environment** (10 entries) - Room setup and agenda availability

## Quick Start

1. **View Results**: Open `index.html` in a web browser
2. **Learn the Method**: Read `GUIDEBOOK.md`
3. **Try it Yourself**: Open `feedback_analysis_tutorial.ipynb` in Jupyter

## Technologies Used

- Python 3.8+
- Google Gemini API for embeddings and analysis
- PostgreSQL for data storage
- UMAP for dimensionality reduction
- HDBSCAN for clustering
- Plotly for interactive visualizations

## Data Overview

- **Total Feedback Entries**: 16,409
- **Entries with Written Feedback**: 5,330 (34.4%)
- **Programs Analyzed**: 24
- **Demo Analysis Size**: 200 entries

## Next Steps

To run a full analysis with real embeddings:

1. Obtain a Google Gemini API key
2. Update the API key in `embedding_analysis_sample.py`
3. Run the script (may take time due to API rate limits)
4. View updated visualizations and results