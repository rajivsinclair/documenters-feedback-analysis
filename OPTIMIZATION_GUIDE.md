# Embedding Analysis Optimization Guide

## Overview

This guide explains the optimized approach for processing 4,926 feedback entries with Google Gemini API while respecting rate limits and ensuring reliability.

## Rate Limit Calculations

### Given Constraints
- **API Rate Limit**: 1,500 requests per minute
- **Safety Factor**: 80% utilization = 1,200 requests per minute
- **Effective Rate**: 20 requests per second
- **Minimum Delay**: 50ms between requests

### Optimal Batch Configuration
- **Embedding Batch Size**: 100 texts per request
- **Total Embedding Requests**: 4,926 ÷ 100 ≈ 50 requests
- **Cluster Description Requests**: ~20-50 (depends on clustering results)
- **Total Requests**: ~70-100 requests
- **Theoretical Minimum Time**: 3.5-5 seconds (API calls only)
- **Actual Time**: 2-5 minutes (including processing overhead)

## Key Optimizations

### 1. Intelligent Batching
- Process embeddings in batches of 100 (Gemini's optimal batch size)
- Batch database operations (1,000 records at a time)
- Parallel cluster description generation (5 workers)

### 2. Rate Limiting
- Thread-safe rate limiter ensures compliance with API limits
- Automatic 50ms delay between requests
- Exponential backoff for retries (2^n seconds)

### 3. Progress Tracking & Recovery
- Checkpoint system saves state every 10 batches
- Automatic recovery from interruptions
- Database tracks processing status per batch
- Skip already-processed embeddings on restart

### 4. Error Handling
- 3 retry attempts per batch with exponential backoff
- Failed entries marked with cluster_id = -2
- Detailed error logging to file and database
- Processing continues despite individual failures

### 5. Performance Features
- Check for existing embeddings before processing
- Incremental database saves
- Optimized UMAP parameters for faster dimensionality reduction
- Concurrent cluster description generation

## Usage

### Running the Optimized Analysis

```bash
# Run the optimized embedding analysis
python embedding_analysis_optimized.py

# Monitor progress in another terminal
python monitor_analysis.py

# Continuous monitoring (updates every 30 seconds)
python monitor_analysis.py --continuous

# Custom update interval
python monitor_analysis.py --continuous --interval 10
```

### Recovery from Interruption

The script automatically handles interruptions:
1. Progress is saved to checkpoints every 10 batches
2. On restart, it loads the latest checkpoint
3. Skips already-processed entries
4. Continues from where it left off

### Database Schema

The optimized version adds several tracking tables:
- `feedback_embeddings`: Stores embeddings with batch tracking
- `processing_log`: Tracks batch processing status and timing
- `analysis_metadata`: Stores analysis parameters and statistics
- Indexes on submission_id, cluster_id, and batch number for fast lookups

## Performance Expectations

### Time Estimates
- **Embedding Generation**: 2-3 minutes for 4,926 entries
- **Clustering**: 30-60 seconds
- **Cluster Descriptions**: 1-2 minutes for 20-50 clusters
- **Total Time**: 4-6 minutes

### Resource Usage
- **Memory**: ~2-3GB for embeddings and clustering
- **Disk**: ~100MB for database and checkpoints
- **CPU**: Moderate usage during UMAP/HDBSCAN clustering

## Monitoring Output

The monitor provides real-time statistics:
- Total processed entries
- Success/failure counts
- Processing rate (batches/minute)
- Cluster distribution
- Estimated completion time
- Recent errors

## Best Practices

1. **Pre-flight Checks**
   - Ensure CSV file exists and is readable
   - Check API key is valid
   - Verify sufficient disk space

2. **During Processing**
   - Don't interrupt unless necessary
   - Monitor progress using monitor_analysis.py
   - Check logs for any errors

3. **Post-Processing**
   - Verify all entries were processed
   - Review cluster descriptions
   - Export results as needed

## Troubleshooting

### Common Issues

1. **Rate Limit Errors**
   - The script automatically handles these with retries
   - If persistent, reduce EFFECTIVE_RATE_LIMIT

2. **Memory Issues**
   - For larger datasets, process in chunks
   - Reduce UMAP n_components if needed

3. **Checkpoint Recovery Fails**
   - Delete corrupted checkpoints in checkpoints/ directory
   - Script will start fresh

4. **Database Locked**
   - Ensure only one instance is running
   - Close any database viewers

## Configuration

Key parameters in `embedding_analysis_optimized.py`:

```python
# Rate limiting
EFFECTIVE_RATE_LIMIT = 1200  # requests per minute
REQUESTS_PER_SECOND = 20     # derived from above

# Batching
EMBEDDING_BATCH_SIZE = 100   # texts per embedding request
CLUSTER_MIN_SIZE = 10        # minimum cluster size

# Retries
MAX_RETRIES = 3              # retry attempts per batch
RETRY_DELAY_BASE = 2         # exponential backoff base
```

Adjust these based on your specific needs and API limits.