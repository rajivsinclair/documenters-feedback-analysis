#!/usr/bin/env python3
"""
Analyze feedback data from PostgreSQL and compare with CSV data
"""

import psycopg2
from psycopg2 import sql
import pandas as pd
import os
from datetime import datetime, timedelta

# Connection string
CONNECTION_STRING = "postgres://supabase:p908ddb2dd908c00289decdc6799d1ae81de44cbcef3b1c05805fabec00291667@ec2-3-213-229-107.compute-1.amazonaws.com:5432/d2jgvhs093s5mk"

def analyze_feedback_data():
    """Analyze feedback data from PostgreSQL"""
    try:
        print("Connecting to PostgreSQL...")
        conn = psycopg2.connect(CONNECTION_STRING)
        cursor = conn.cursor()
        
        print("✓ Connected successfully!")
        
        # First, let's explore the assignments_feedback table structure
        print("\n1. Exploring assignments_feedback table structure...")
        cursor.execute("""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'assignments_feedback'
            ORDER BY ordinal_position;
        """)
        
        columns = cursor.fetchall()
        print("\nColumns in assignments_feedback:")
        feedback_columns = []
        for col_name, data_type, max_length in columns:
            feedback_columns.append(col_name)
            print(f"  - {col_name}: {data_type}" + (f"({max_length})" if max_length else ""))
        
        # Get sample data to understand the structure
        print("\n2. Sample data from assignments_feedback:")
        cursor.execute("SELECT * FROM assignments_feedback LIMIT 5")
        sample_data = cursor.fetchall()
        
        # Create a dataframe for better display
        df_sample = pd.DataFrame(sample_data, columns=feedback_columns)
        print(df_sample.to_string(max_cols=10, max_colwidth=50))
        
        # Look for program information in related tables
        print("\n3. Looking for program information...")
        
        # Check if there's a direct program column or we need to join
        if 'program' in feedback_columns or 'program_id' in feedback_columns or 'program_name' in feedback_columns:
            print("Found program column in assignments_feedback table")
        else:
            print("No direct program column found. Checking for relationships...")
            
            # Look for foreign key relationships
            cursor.execute("""
                SELECT 
                    tc.constraint_name,
                    tc.table_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY' 
                    AND tc.table_name = 'assignments_feedback';
            """)
            
            relationships = cursor.fetchall()
            print(f"\nFound {len(relationships)} foreign key relationships:")
            for rel in relationships:
                print(f"  - {rel[2]} -> {rel[3]}.{rel[4]}")
        
        # Check for documenters_feedback column (filled vs blank)
        print("\n4. Analyzing feedback content...")
        
        # Look for the actual feedback column
        feedback_column = None
        for col in feedback_columns:
            if 'feedback' in col.lower() and 'documenters' in col.lower():
                feedback_column = col
                break
        
        if not feedback_column:
            # Try to find any feedback-related column
            for col in feedback_columns:
                if 'feedback' in col.lower() or 'comment' in col.lower() or 'text' in col.lower():
                    feedback_column = col
                    break
        
        if feedback_column:
            print(f"Using column '{feedback_column}' for feedback analysis")
            
            # Count filled vs blank feedback
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN {feedback_column} IS NOT NULL AND TRIM({feedback_column}) != '' THEN 1 END) as filled,
                    COUNT(CASE WHEN {feedback_column} IS NULL OR TRIM({feedback_column}) = '' THEN 1 END) as blank
                FROM assignments_feedback
            """)
            
            total, filled, blank = cursor.fetchone()
            print(f"\nOverall feedback statistics:")
            print(f"  Total submissions: {total:,}")
            print(f"  Filled feedback: {filled:,}")
            print(f"  Blank feedback: {blank:,}")
            print(f"  Fill rate: {(filled/total*100):.2f}%")
        
        # Try to find program information through joins
        print("\n5. Attempting to get program-level statistics...")
        
        # First, let's see what tables might contain program info
        cursor.execute("""
            SELECT DISTINCT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND (table_name LIKE '%program%' OR table_name LIKE '%project%' OR table_name LIKE '%city%' OR table_name LIKE '%location%')
            ORDER BY table_name;
        """)
        
        program_tables = cursor.fetchall()
        print(f"\nPotential program-related tables:")
        for (table,) in program_tables:
            print(f"  - {table}")
        
        # Look for assignment table that might link feedback to programs
        cursor.execute("""
            SELECT DISTINCT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE '%assignment%'
            ORDER BY table_name;
        """)
        
        assignment_tables = cursor.fetchall()
        print(f"\nAssignment-related tables:")
        for (table,) in assignment_tables:
            print(f"  - {table}")
            
            # Get columns for this table
            cursor.execute(f"""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position
                LIMIT 10;
            """, (table,))
            
            cols = cursor.fetchall()
            print(f"    Columns: {', '.join([c[0] for c in cols])}")
        
        # Load CSV data for comparison
        print("\n6. Loading CSV data for comparison...")
        csv_df = pd.read_csv('/Users/j/GitHub/documenters-feedback-analysis/documenters_feedback_stats.csv')
        print(f"CSV contains {len(csv_df)} programs")
        print(f"Total submissions in CSV: {csv_df['total_submissions_all_time'].sum():,}")
        print(f"Total filled feedback in CSV: {csv_df['filled_documenters_feedback_all_time'].sum():,}")
        
        cursor.close()
        conn.close()
        print("\n✓ Analysis completed!")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        print(f"Error type: {type(e).__name__}")

def explore_table_relationships():
    """Explore relationships between tables to find program information"""
    try:
        conn = psycopg2.connect(CONNECTION_STRING)
        cursor = conn.cursor()
        
        print("\n7. Deep dive into table relationships...")
        
        # Get all columns from assignments_feedback that might be IDs
        cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public' 
            AND table_name = 'assignments_feedback'
            AND (column_name LIKE '%_id' OR column_name = 'id' OR data_type IN ('integer', 'bigint', 'uuid'))
            ORDER BY ordinal_position;
        """)
        
        id_columns = cursor.fetchall()
        print("\nPotential ID columns in assignments_feedback:")
        for col_name, data_type in id_columns:
            print(f"  - {col_name}: {data_type}")
            
            # For each ID column, check if it appears in other tables
            cursor.execute("""
                SELECT DISTINCT table_name, column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' 
                AND column_name = %s
                AND table_name != 'assignments_feedback'
                LIMIT 5;
            """, (col_name,))
            
            matching_tables = cursor.fetchall()
            if matching_tables:
                print(f"    Found in: {', '.join([t[0] for t in matching_tables])}")
        
        # Try to construct a query to get program information
        print("\n8. Attempting to join tables to get program information...")
        
        # First, check if there's an assignments table
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'assignments'
        """)
        
        if cursor.fetchone()[0] > 0:
            print("Found 'assignments' table. Exploring structure...")
            
            cursor.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'assignments'
                ORDER BY ordinal_position
                LIMIT 20;
            """)
            
            assignment_cols = cursor.fetchall()
            print("Columns in assignments table:")
            for col_name, data_type in assignment_cols:
                print(f"  - {col_name}: {data_type}")
            
            # Try a sample join
            print("\nSample join between assignments_feedback and assignments:")
            cursor.execute("""
                SELECT af.*, a.*
                FROM assignments_feedback af
                LEFT JOIN assignments a ON af.assignment_id = a.id
                LIMIT 2
            """)
            
            # Get column names for the joined result
            col_names = [desc[0] for desc in cursor.description]
            print(f"Join produces {len(col_names)} columns")
            
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"\n✗ Error in relationship exploration: {e}")

if __name__ == "__main__":
    analyze_feedback_data()
    explore_table_relationships()