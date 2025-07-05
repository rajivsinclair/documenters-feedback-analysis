#!/usr/bin/env python3
"""
Compare SQLite database statistics with CSV file to verify data accuracy
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import json

def get_sqlite_stats():
    """Get statistics from SQLite database"""
    
    conn = sqlite3.connect('feedback_analysis.db')
    
    # Get all-time statistics
    all_time_query = """
    SELECT 
        program_name,
        COUNT(*) as total_submissions,
        SUM(CASE WHEN feedback IS NOT NULL AND TRIM(feedback) != '' THEN 1 ELSE 0 END) as filled,
        SUM(CASE WHEN feedback IS NULL OR TRIM(feedback) = '' THEN 1 ELSE 0 END) as blank
    FROM feedback_embeddings
    GROUP BY program_name
    ORDER BY program_name
    """
    
    all_time_df = pd.read_sql_query(all_time_query, conn)
    all_time_df['filled_percentage'] = (all_time_df['filled'] / all_time_df['total_submissions'] * 100).round(1)
    
    # Get 12-month statistics
    twelve_months_ago = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    
    twelve_month_query = f"""
    SELECT 
        program_name,
        COUNT(*) as total_submissions_12mo,
        SUM(CASE WHEN feedback IS NOT NULL AND TRIM(feedback) != '' THEN 1 ELSE 0 END) as filled_12mo,
        SUM(CASE WHEN feedback IS NULL OR TRIM(feedback) = '' THEN 1 ELSE 0 END) as blank_12mo
    FROM feedback_embeddings
    WHERE created_at >= '{twelve_months_ago}'
    GROUP BY program_name
    ORDER BY program_name
    """
    
    twelve_month_df = pd.read_sql_query(twelve_month_query, conn)
    twelve_month_df['filled_percentage_12mo'] = (twelve_month_df['filled_12mo'] / twelve_month_df['total_submissions_12mo'] * 100).round(1)
    
    # Merge the dataframes
    sqlite_stats = pd.merge(all_time_df, twelve_month_df, on='program_name', how='outer')
    
    conn.close()
    
    return sqlite_stats

def get_csv_stats():
    """Get statistics from CSV file"""
    return pd.read_csv('documenters_feedback_stats.csv')

def compare_stats():
    """Compare SQLite and CSV statistics"""
    
    print("Loading data from both sources...")
    sqlite_stats = get_sqlite_stats()
    csv_stats = get_csv_stats()
    
    print(f"\nSQLite programs: {len(sqlite_stats)}")
    print(f"CSV programs: {len(csv_stats)}")
    
    # Check for missing programs
    sqlite_programs = set(sqlite_stats['program_name'])
    csv_programs = set(csv_stats['program_name'])
    
    missing_in_csv = sqlite_programs - csv_programs
    missing_in_sqlite = csv_programs - sqlite_programs
    
    if missing_in_csv:
        print(f"\nPrograms in SQLite but not in CSV: {missing_in_csv}")
    if missing_in_sqlite:
        print(f"\nPrograms in CSV but not in SQLite: {missing_in_sqlite}")
    
    # Compare statistics for common programs
    print("\nComparing statistics for common programs:")
    print("-" * 80)
    
    common_programs = sqlite_programs & csv_programs
    
    discrepancies = []
    
    for program in sorted(common_programs):
        sqlite_row = sqlite_stats[sqlite_stats['program_name'] == program].iloc[0]
        csv_row = csv_stats[csv_stats['program_name'] == program].iloc[0]
        
        # Compare all-time stats
        all_time_match = (
            sqlite_row['total_submissions'] == csv_row['total_submissions_all_time'] and
            sqlite_row['filled'] == csv_row['filled_documenters_feedback_all_time'] and
            sqlite_row['blank'] == csv_row['blank_documenters_feedback_all_time']
        )
        
        if not all_time_match:
            print(f"\n{program} - ALL-TIME MISMATCH:")
            print(f"  SQLite: Total={sqlite_row['total_submissions']}, Filled={sqlite_row['filled']}, Blank={sqlite_row['blank']}")
            print(f"  CSV:    Total={csv_row['total_submissions_all_time']}, Filled={csv_row['filled_documenters_feedback_all_time']}, Blank={csv_row['blank_documenters_feedback_all_time']}")
            discrepancies.append(program)
    
    if not discrepancies:
        print("\nAll statistics match between SQLite and CSV!")
    else:
        print(f"\nFound discrepancies in {len(discrepancies)} programs")
    
    # Check if SQLite has the data issue (all feedback marked as filled)
    print("\nChecking for data quality issues...")
    empty_feedback_query = """
    SELECT COUNT(*) as empty_count 
    FROM feedback_embeddings 
    WHERE feedback IS NULL OR TRIM(feedback) = ''
    """
    conn = sqlite3.connect('feedback_analysis.db')
    empty_count = pd.read_sql_query(empty_feedback_query, conn).iloc[0]['empty_count']
    conn.close()
    
    print(f"Total empty feedback entries in SQLite: {empty_count}")
    
    if empty_count == 0:
        print("\nWARNING: SQLite database shows no empty feedback entries!")
        print("This suggests the data may have been filtered to include only filled feedback.")
        print("We should use the CSV data as the authoritative source for statistics.")

if __name__ == "__main__":
    compare_stats()