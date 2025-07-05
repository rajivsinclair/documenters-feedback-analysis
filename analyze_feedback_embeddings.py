#!/usr/bin/env python3
"""
Analyze feedback_embeddings table in SQLite databases.
"""

import sqlite3
import pandas as pd
import json

def analyze_feedback_embeddings(db_path):
    """Analyze the feedback_embeddings table."""
    conn = sqlite3.connect(db_path)
    
    try:
        # Get column info
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(feedback_embeddings)")
        columns = cursor.fetchall()
        print("\nColumns in feedback_embeddings:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
        
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM feedback_embeddings")
        total_count = cursor.fetchone()[0]
        print(f"\nTotal feedback entries: {total_count:,}")
        
        # Get sample data
        df_sample = pd.read_sql_query("SELECT * FROM feedback_embeddings LIMIT 5", conn)
        print("\nSample entries:")
        for idx, row in df_sample.iterrows():
            print(f"\n--- Entry {idx + 1} ---")
            for col in df_sample.columns:
                if col != 'embedding':  # Skip embedding column as it's too large
                    print(f"{col}: {row[col]}")
        
        # Analyze programs
        # First check if there's a direct program column
        df_all = pd.read_sql_query("SELECT * FROM feedback_embeddings", conn)
        
        # Look for program information in various columns
        program_found = False
        
        # Check for program_name column
        if 'program_name' in df_all.columns:
            program_found = True
            program_counts = df_all['program_name'].value_counts()
        
        # Check for program in other columns
        elif 'program' in df_all.columns:
            program_found = True
            program_counts = df_all['program'].value_counts()
            
        # Check if program info is in JSON metadata
        elif 'metadata' in df_all.columns:
            print("\nExtracting program information from metadata...")
            programs = []
            for _, row in df_all.iterrows():
                try:
                    metadata = json.loads(row['metadata']) if isinstance(row['metadata'], str) else row['metadata']
                    if isinstance(metadata, dict):
                        program = metadata.get('program') or metadata.get('program_name') or metadata.get('assignment_program')
                        if program:
                            programs.append(program)
                except:
                    pass
            
            if programs:
                program_found = True
                program_counts = pd.Series(programs).value_counts()
        
        # Check the meeting_type column
        elif 'meeting_type' in df_all.columns:
            print("\nUsing meeting_type as program identifier...")
            program_found = True
            program_counts = df_all['meeting_type'].value_counts()
        
        if program_found:
            print(f"\n{'='*60}")
            print("FEEDBACK ENTRIES PER PROGRAM")
            print(f"{'='*60}")
            print(f"{'Program':<40} {'Count':>10} {'Percentage':>10}")
            print("-" * 70)
            
            total = program_counts.sum()
            for program, count in program_counts.items():
                if program and str(program).strip():  # Skip empty values
                    percentage = (count / total) * 100
                    print(f"{str(program)[:40]:<40} {count:>10,} {percentage:>9.1f}%")
            
            print("-" * 70)
            print(f"{'TOTAL':<40} {total:>10,} {'100.0%':>10}")
            print(f"\nNumber of unique programs: {len(program_counts)}")
            
            # Complete list of programs
            print(f"\n{'='*60}")
            print("COMPLETE LIST OF ALL PROGRAMS")
            print(f"{'='*60}")
            for i, (program, count) in enumerate(program_counts.items()):
                if program and str(program).strip():
                    print(f"{i+1:3d}. {program} ({count:,} entries)")
        else:
            print("\nNo clear program column found. Here are all available columns:")
            for col in df_all.columns:
                if col != 'embedding':
                    print(f"  - {col}")
                    if df_all[col].dtype == 'object':
                        unique_count = df_all[col].nunique()
                        if unique_count > 1 and unique_count < 100:
                            print(f"    Unique values: {unique_count}")
                            print(f"    Sample values: {df_all[col].dropna().unique()[:5].tolist()}")
        
        # Also check for meeting_type_analysis table
        try:
            df_meeting_types = pd.read_sql_query("SELECT * FROM meeting_type_analysis", conn)
            if not df_meeting_types.empty:
                print(f"\n{'='*60}")
                print("MEETING TYPE ANALYSIS")
                print(f"{'='*60}")
                print(df_meeting_types.to_string(index=False))
        except:
            pass
            
    except Exception as e:
        print(f"Error analyzing feedback_embeddings: {e}")
    
    conn.close()

# Analyze the main database
print("ANALYZING FEEDBACK DATABASE")
print("=" * 80)

db_path = "./feedback_analysis.db"
analyze_feedback_embeddings(db_path)