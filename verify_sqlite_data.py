#!/usr/bin/env python3
"""
Verify if SQLite database contains sufficient data for statistics validation
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import sys

def check_sqlite_database():
    """Check SQLite database structure and data availability"""
    
    db_path = 'feedback_analysis.db'
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("Connected to SQLite database")
        print("\nChecking available tables...")
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"Available tables: {[t[0] for t in tables]}")
        
        # Check feedback_embeddings table structure
        print("\nChecking feedback_embeddings table structure...")
        cursor.execute("PRAGMA table_info(feedback_embeddings);")
        columns = cursor.fetchall()
        print("Columns in feedback_embeddings:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
        
        # Check data availability
        print("\nChecking data availability...")
        cursor.execute("SELECT COUNT(*) FROM feedback_embeddings")
        total_count = cursor.fetchone()[0]
        print(f"Total feedback entries: {total_count}")
        
        # Check program names
        cursor.execute("SELECT DISTINCT program_name FROM feedback_embeddings ORDER BY program_name")
        programs = [p[0] for p in cursor.fetchall()]
        print(f"\nPrograms in database ({len(programs)} total):")
        for p in programs:
            print(f"  - {p}")
        
        # Check date range
        cursor.execute("SELECT MIN(created_at), MAX(created_at) FROM feedback_embeddings")
        min_date, max_date = cursor.fetchone()
        print(f"\nDate range: {min_date} to {max_date}")
        
        # Sample program statistics
        print("\nSample statistics for verification:")
        for program in programs[:5]:  # First 5 programs
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN feedback IS NOT NULL AND feedback != '' THEN 1 ELSE 0 END) as filled,
                    SUM(CASE WHEN feedback IS NULL OR feedback = '' THEN 1 ELSE 0 END) as blank
                FROM feedback_embeddings 
                WHERE program_name = ?
            """, (program,))
            total, filled, blank = cursor.fetchone()
            print(f"\n{program}:")
            print(f"  Total: {total}")
            print(f"  Filled: {filled}")
            print(f"  Blank: {blank}")
            print(f"  Filled %: {(filled/total*100):.1f}%" if total > 0 else "N/A")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    check_sqlite_database()