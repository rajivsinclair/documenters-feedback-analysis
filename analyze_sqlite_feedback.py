#!/usr/bin/env python3
"""
Analyze SQLite feedback database for program statistics.
"""

import sqlite3
import pandas as pd
from collections import Counter

def analyze_feedback_database(db_path):
    """Analyze the feedback database and provide summary statistics."""
    conn = sqlite3.connect(db_path)
    
    # First, let's see what tables we have
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"Tables in {db_path}:")
    for table in tables:
        print(f"  - {table[0]}")
    
    # Try to find feedback data
    # Check if there's a feedback table
    try:
        # Get all data from feedback table
        query = "SELECT * FROM feedback LIMIT 5"
        df_sample = pd.read_sql_query(query, conn)
        print(f"\nSample data from feedback table:")
        print(df_sample)
        
        # Get column names
        cursor.execute("PRAGMA table_info(feedback)")
        columns = cursor.fetchall()
        print("\nColumns in feedback table:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
        
        # Count feedback entries per program
        # Look for program-related columns
        program_columns = [col[1] for col in columns if 'program' in col[1].lower()]
        
        if program_columns:
            program_col = program_columns[0]
            query = f"""
            SELECT {program_col}, COUNT(*) as feedback_count
            FROM feedback
            GROUP BY {program_col}
            ORDER BY feedback_count DESC
            """
            df_programs = pd.read_sql_query(query, conn)
            
            print(f"\n{'='*60}")
            print("FEEDBACK ENTRIES PER PROGRAM")
            print(f"{'='*60}")
            print(f"{'Program':<40} {'Count':>10}")
            print("-" * 60)
            
            total = 0
            for _, row in df_programs.iterrows():
                program = row[program_col] if row[program_col] else "Unknown"
                count = row['feedback_count']
                total += count
                print(f"{program:<40} {count:>10,}")
            
            print("-" * 60)
            print(f"{'TOTAL':<40} {total:>10,}")
            print(f"\nNumber of unique programs: {len(df_programs)}")
            
            # Get complete list of programs
            print(f"\n{'='*60}")
            print("COMPLETE LIST OF ALL PROGRAMS")
            print(f"{'='*60}")
            for i, row in df_programs.iterrows():
                program = row[program_col] if row[program_col] else "Unknown"
                print(f"{i+1:3d}. {program}")
                
        else:
            # If no program column, look for other identifying information
            print("\nNo 'program' column found. Looking for other identifying columns...")
            # Try to read all data and analyze
            df_all = pd.read_sql_query("SELECT * FROM feedback", conn)
            print(f"\nTotal feedback entries: {len(df_all)}")
            
            # Look for any categorical columns that might represent programs
            for col in df_all.columns:
                if df_all[col].dtype == 'object':
                    unique_values = df_all[col].nunique()
                    if 2 <= unique_values <= 50:  # Reasonable range for programs
                        print(f"\nPossible program column: {col}")
                        value_counts = df_all[col].value_counts()
                        print(value_counts.head(20))
                        
    except Exception as e:
        print(f"Error analyzing feedback table: {e}")
        
        # Try alternative table names
        for table_name in ['responses', 'submissions', 'questionnaire_responses', 'survey_responses']:
            try:
                df_test = pd.read_sql_query(f"SELECT * FROM {table_name} LIMIT 1", conn)
                print(f"\nFound table: {table_name}")
                analyze_table(conn, table_name)
                break
            except:
                continue
    
    conn.close()

def analyze_table(conn, table_name):
    """Analyze a specific table for program information."""
    cursor = conn.cursor()
    
    # Get column info
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    print(f"\nColumns in {table_name}:")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")
    
    # Read data
    df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    print(f"\nTotal entries: {len(df)}")
    
    # Look for program-related columns
    for col in df.columns:
        if 'program' in col.lower() or 'project' in col.lower():
            print(f"\nAnalyzing column: {col}")
            value_counts = df[col].value_counts()
            print(value_counts)

# Analyze all found databases
print("ANALYZING SQLITE DATABASES")
print("=" * 80)

databases = [
    "./feedback_analysis.db",
    "./feedback_analysis_demo.db",
    "./feedback_analysis_sample.db",
    "./embedding_analysis.db"
]

for db_path in databases:
    print(f"\n\n{'='*80}")
    print(f"Analyzing: {db_path}")
    print(f"{'='*80}")
    try:
        analyze_feedback_database(db_path)
    except Exception as e:
        print(f"Error analyzing {db_path}: {e}")