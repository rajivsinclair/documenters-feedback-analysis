#!/usr/bin/env python3
"""
Monitor the progress of the feedback analysis
"""

import sqlite3
import time
import sys
from datetime import datetime
import argparse

DB_PATH = "feedback_analysis.db"

def get_analysis_stats():
    """Get current analysis statistics."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    stats = {}
    
    # Overall progress
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN embedding IS NOT NULL THEN 1 ELSE 0 END) as processed,
            SUM(CASE WHEN processing_status = 'failed' THEN 1 ELSE 0 END) as failed,
            COUNT(DISTINCT cluster_id) - 1 as num_clusters
        FROM feedback_embeddings
    """)
    row = cursor.fetchone()
    stats['total_entries'] = row[0]
    stats['processed'] = row[1]
    stats['failed'] = row[2]
    stats['num_clusters'] = max(0, row[3])
    
    # Clustering stats
    cursor.execute("""
        SELECT 
            SUM(CASE WHEN cluster_id >= 0 THEN 1 ELSE 0 END) as clustered,
            SUM(CASE WHEN cluster_id = -1 THEN 1 ELSE 0 END) as noise
        FROM feedback_embeddings
        WHERE embedding IS NOT NULL
    """)
    row = cursor.fetchone()
    stats['clustered'] = row[0] or 0
    stats['noise'] = row[1] or 0
    
    # Current phase
    cursor.execute("""
        SELECT analysis_phase, total_samples, processed_samples, start_time
        FROM analysis_metadata
        ORDER BY id DESC
        LIMIT 1
    """)
    row = cursor.fetchone()
    if row:
        stats['phase'] = row[0]
        stats['phase_total'] = row[1]
        stats['phase_processed'] = row[2]
        stats['phase_start'] = row[3]
    else:
        stats['phase'] = 'Not started'
    
    # Batch performance
    cursor.execute("""
        SELECT 
            COUNT(*) as completed_batches,
            AVG(processing_time) as avg_time,
            SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_batches
        FROM batch_progress
    """)
    row = cursor.fetchone()
    stats['completed_batches'] = row[0] or 0
    stats['avg_batch_time'] = row[1] or 0
    stats['failed_batches'] = row[2] or 0
    
    # Recent errors
    cursor.execute("""
        SELECT COUNT(*) 
        FROM feedback_embeddings 
        WHERE error_message IS NOT NULL
        AND updated_at > datetime('now', '-5 minutes')
    """)
    stats['recent_errors'] = cursor.fetchone()[0]
    
    conn.close()
    return stats

def format_time_remaining(processed, total, start_time):
    """Estimate time remaining."""
    if processed == 0:
        return "Unknown"
    
    elapsed = (datetime.now() - datetime.fromisoformat(start_time)).total_seconds()
    rate = processed / elapsed
    remaining = (total - processed) / rate if rate > 0 else 0
    
    if remaining < 60:
        return f"{int(remaining)}s"
    elif remaining < 3600:
        return f"{int(remaining/60)}m"
    else:
        return f"{int(remaining/3600)}h {int((remaining%3600)/60)}m"

def display_progress(stats):
    """Display progress in a nice format."""
    print("\033[2J\033[H")  # Clear screen
    print("="*60)
    print("FEEDBACK ANALYSIS MONITOR")
    print("="*60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Overall progress
    if stats['total_entries'] > 0:
        progress = stats['processed'] / stats['total_entries'] * 100
        bar_length = 40
        filled = int(bar_length * stats['processed'] / stats['total_entries'])
        bar = '█' * filled + '░' * (bar_length - filled)
        
        print(f"Overall Progress: [{bar}] {progress:.1f}%")
        print(f"Processed: {stats['processed']:,} / {stats['total_entries']:,}")
        print(f"Failed: {stats['failed']:,}")
        print()
    
    # Current phase
    print(f"Current Phase: {stats['phase']}")
    if stats['phase'] == 'embedding_generation' and 'phase_start' in stats:
        phase_progress = stats['phase_processed'] / stats['phase_total'] * 100 if stats['phase_total'] > 0 else 0
        print(f"Phase Progress: {stats['phase_processed']:,} / {stats['phase_total']:,} ({phase_progress:.1f}%)")
        print(f"Est. Time Remaining: {format_time_remaining(stats['phase_processed'], stats['phase_total'], stats['phase_start'])}")
    print()
    
    # Clustering results
    if stats['clustered'] > 0:
        print(f"Clustering Results:")
        print(f"  Clusters Found: {stats['num_clusters']}")
        print(f"  Clustered: {stats['clustered']:,}")
        print(f"  Noise: {stats['noise']:,}")
        print()
    
    # Performance metrics
    if stats['completed_batches'] > 0:
        print(f"Batch Performance:")
        print(f"  Completed: {stats['completed_batches']}")
        print(f"  Failed: {stats['failed_batches']}")
        print(f"  Avg Time: {stats['avg_batch_time']:.2f}s")
        print(f"  Est. Throughput: {100/stats['avg_batch_time']:.1f} entries/sec")
    
    if stats['recent_errors'] > 0:
        print(f"\n⚠️  Recent errors: {stats['recent_errors']} (last 5 min)")
    
    print("\nPress Ctrl+C to exit")

def main():
    parser = argparse.ArgumentParser(description='Monitor feedback analysis progress')
    parser.add_argument('--interval', type=int, default=5, help='Update interval in seconds')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    parser.add_argument('--continuous', action='store_true', help='Run continuously')
    
    args = parser.parse_args()
    
    try:
        while True:
            stats = get_analysis_stats()
            display_progress(stats)
            
            if args.once:
                break
                
            time.sleep(args.interval)
            
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()