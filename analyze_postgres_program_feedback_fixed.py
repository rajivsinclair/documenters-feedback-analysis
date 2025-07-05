#!/usr/bin/env python3
"""
Analyze feedback data by program from PostgreSQL - Fixed version
"""

import psycopg2
import pandas as pd
from datetime import datetime, timedelta

# Connection string
CONNECTION_STRING = "postgres://supabase:p908ddb2dd908c00289decdc6799d1ae81de44cbcef3b1c05805fabec00291667@ec2-3-213-229-107.compute-1.amazonaws.com:5432/d2jgvhs093s5mk"

def analyze_program_feedback():
    """Analyze feedback data by program"""
    try:
        print("Connecting to PostgreSQL...")
        conn = psycopg2.connect(CONNECTION_STRING)
        cursor = conn.cursor()
        
        print("✓ Connected successfully!")
        
        # Get sample program data
        print("\n1. Available programs in the database:")
        cursor.execute("""
            SELECT id, name, created_at, active
            FROM accounts_program
            WHERE active = true
            ORDER BY name
        """)
        
        programs = cursor.fetchall()
        print(f"\nFound {len(programs)} active programs:")
        for prog in programs[:10]:  # Show first 10
            print(f"  ID: {prog[0]}, Name: {prog[1]}, Created: {prog[2]}")
        
        # Now let's get feedback statistics by program
        print("\n2. Calculating feedback statistics by program...")
        
        # First, let's understand the data model better
        cursor.execute("""
            SELECT 
                p.name as program_name,
                COUNT(DISTINCT a.id) as assignment_count,
                COUNT(DISTINCT r.id) as role_count,
                COUNT(DISTINCT af.id) as feedback_count
            FROM accounts_program p
            LEFT JOIN assignments_assignment a ON a.program_id = p.id
            LEFT JOIN assignments_role r ON r.assignment_id = a.id
            LEFT JOIN assignments_feedback af ON af.role_id = r.id
            WHERE p.active = true
            GROUP BY p.id, p.name
            HAVING COUNT(DISTINCT af.id) > 0
            ORDER BY feedback_count DESC
        """)
        
        program_stats = cursor.fetchall()
        
        print(f"\nPrograms with feedback data:")
        df_stats = pd.DataFrame(program_stats, 
                              columns=['Program', 'Assignments', 'Roles', 'Feedback'])
        print(df_stats.to_string(index=False))
        
        # Now let's analyze the feedback content
        print("\n3. Analyzing feedback content (filled vs blank)...")
        
        # The assignments_feedback table seems to have ALL non-null comments
        # Let's check if there's another table with the actual documenters feedback
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND (table_name LIKE '%documenter%' OR table_name LIKE '%submission%')
            ORDER BY table_name;
        """)
        
        documenter_tables = cursor.fetchall()
        print("\nTables that might contain documenter feedback:")
        for (table,) in documenter_tables:
            print(f"  - {table}")
        
        # Check the assignments_submission table more closely
        print("\n4. Analyzing assignments_submission data...")
        cursor.execute("""
            SELECT 
                p.name as program_name,
                COUNT(DISTINCT s.id) as total_submissions,
                COUNT(DISTINCT CASE WHEN s.notes IS NOT NULL AND TRIM(s.notes) != '' THEN s.id END) as filled_notes,
                COUNT(DISTINCT CASE WHEN s.notes IS NULL OR TRIM(s.notes) = '' THEN s.id END) as blank_notes,
                COUNT(DISTINCT CASE WHEN s.data IS NOT NULL THEN s.id END) as has_data
            FROM assignments_submission s
            JOIN assignments_role r ON s.role_id = r.id
            JOIN assignments_assignment a ON r.assignment_id = a.id
            JOIN accounts_program p ON a.program_id = p.id
            WHERE p.active = true
            GROUP BY p.id, p.name
            ORDER BY total_submissions DESC
        """)
        
        submission_stats = cursor.fetchall()
        
        print(f"\nSubmission statistics by program:")
        df_submissions = pd.DataFrame(submission_stats, 
                                    columns=['Program', 'Total Submissions', 'Filled Notes', 'Blank Notes', 'Has Data'])
        df_submissions['Notes Fill Rate %'] = (df_submissions['Filled Notes'] / df_submissions['Total Submissions'] * 100).round(2)
        print(df_submissions.to_string(index=False))
        
        # Check what's in the data column
        print("\n5. Checking submission data column for documenter feedback...")
        cursor.execute("""
            SELECT 
                s.data,
                p.name as program_name
            FROM assignments_submission s
            JOIN assignments_role r ON s.role_id = r.id
            JOIN assignments_assignment a ON r.assignment_id = a.id
            JOIN accounts_program p ON a.program_id = p.id
            WHERE s.data IS NOT NULL
            AND p.active = true
            LIMIT 5
        """)
        
        sample_data = cursor.fetchall()
        print("\nSample submission data:")
        for i, (data, program) in enumerate(sample_data, 1):
            print(f"\n{i}. Program: {program}")
            if isinstance(data, dict):
                print(f"   Data keys: {list(data.keys())[:10]}")
                # Look for documenter_feedback key
                if 'documenter_feedback' in data:
                    print(f"   Documenter feedback: {data['documenter_feedback'][:100]}...")
                elif 'documenters_feedback' in data:
                    print(f"   Documenters feedback: {data['documenters_feedback'][:100]}...")
        
        # Now let's try to extract documenter feedback from the data column
        print("\n6. Extracting documenter feedback from submission data...")
        cursor.execute("""
            SELECT 
                p.name as program_name,
                COUNT(DISTINCT s.id) as total_submissions,
                COUNT(DISTINCT CASE 
                    WHEN s.data->>'documenter_feedback' IS NOT NULL 
                    AND TRIM(s.data->>'documenter_feedback') != '' 
                    THEN s.id 
                END) as filled_feedback,
                COUNT(DISTINCT CASE 
                    WHEN s.data->>'documenter_feedback' IS NULL 
                    OR TRIM(s.data->>'documenter_feedback') = '' 
                    THEN s.id 
                END) as blank_feedback
            FROM assignments_submission s
            JOIN assignments_role r ON s.role_id = r.id
            JOIN assignments_assignment a ON r.assignment_id = a.id
            JOIN accounts_program p ON a.program_id = p.id
            WHERE p.active = true
            GROUP BY p.id, p.name
            HAVING COUNT(DISTINCT s.id) > 0
            ORDER BY total_submissions DESC
        """)
        
        feedback_results = cursor.fetchall()
        
        print(f"\nDocumenter feedback statistics by program:")
        df_feedback = pd.DataFrame(feedback_results, 
                                 columns=['Program', 'Total', 'Filled', 'Blank'])
        df_feedback['Fill Rate %'] = df_feedback.apply(
            lambda row: round(row['Filled'] / row['Total'] * 100, 2) if row['Total'] > 0 else 0, 
            axis=1
        )
        
        print(df_feedback.to_string(index=False))
        
        # Calculate totals
        total_submissions = df_feedback['Total'].sum()
        total_filled = df_feedback['Filled'].sum()
        total_blank = df_feedback['Blank'].sum()
        
        print(f"\nOverall totals from PostgreSQL:")
        print(f"  Total submissions: {total_submissions:,}")
        print(f"  Filled feedback: {total_filled:,}")
        print(f"  Blank feedback: {total_blank:,}")
        print(f"  Overall fill rate: {(total_filled/total_submissions*100 if total_submissions > 0 else 0):.2f}%")
        
        # Compare with CSV data
        print("\n7. Comparing with CSV data...")
        csv_df = pd.read_csv('/Users/j/GitHub/documenters-feedback-analysis/documenters_feedback_stats.csv')
        
        print(f"\nCSV Summary:")
        print(f"  Programs: {len(csv_df)}")
        print(f"  Total submissions: {csv_df['total_submissions_all_time'].sum():,}")
        print(f"  Total filled: {csv_df['filled_documenters_feedback_all_time'].sum():,}")
        print(f"  Total blank: {csv_df['blank_documenters_feedback_all_time'].sum():,}")
        
        # Try to match programs
        print("\n8. Matching programs between PostgreSQL and CSV:")
        for _, row in df_feedback.head(10).iterrows():
            pg_program = row['Program']
            # Look for match in CSV
            csv_match = csv_df[csv_df['program_name'].str.lower() == pg_program.lower()]
            if not csv_match.empty:
                csv_row = csv_match.iloc[0]
                print(f"\n{pg_program}:")
                print(f"  PostgreSQL - Total: {row['Total']:,}, Filled: {row['Filled']:,}, Blank: {row['Blank']:,}")
                print(f"  CSV - Total: {csv_row['total_submissions_all_time']:,}, Filled: {csv_row['filled_documenters_feedback_all_time']:,}, Blank: {csv_row['blank_documenters_feedback_all_time']:,}")
        
        # Export the PostgreSQL results for comparison
        output_file = '/Users/j/GitHub/documenters-feedback-analysis/postgres_feedback_stats.csv'
        df_feedback.to_csv(output_file, index=False)
        print(f"\n✓ PostgreSQL results exported to: {output_file}")
        
        cursor.close()
        conn.close()
        print("\n✓ Analysis completed!")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()

def check_data_json_structure():
    """Deep dive into the JSON structure of the data column"""
    try:
        conn = psycopg2.connect(CONNECTION_STRING)
        cursor = conn.cursor()
        
        print("\n9. Deep analysis of submission data JSON structure...")
        
        # Get all unique keys in the data column
        cursor.execute("""
            SELECT DISTINCT jsonb_object_keys(data) as key
            FROM assignments_submission
            WHERE data IS NOT NULL
            ORDER BY key
        """)
        
        keys = cursor.fetchall()
        print(f"\nUnique keys found in submission data:")
        for (key,) in keys:
            print(f"  - {key}")
            
        # Check if any key contains 'feedback' or 'documenter'
        feedback_keys = [k[0] for k in keys if 'feedback' in k[0].lower() or 'documenter' in k[0].lower()]
        if feedback_keys:
            print(f"\nFeedback-related keys: {feedback_keys}")
        
        # Sample some actual data values
        cursor.execute("""
            SELECT 
                data,
                p.name as program_name
            FROM assignments_submission s
            JOIN assignments_role r ON s.role_id = r.id
            JOIN assignments_assignment a ON r.assignment_id = a.id
            JOIN accounts_program p ON a.program_id = p.id
            WHERE data IS NOT NULL
            AND jsonb_typeof(data) = 'object'
            LIMIT 10
        """)
        
        samples = cursor.fetchall()
        print(f"\n10 sample data entries:")
        for i, (data, program) in enumerate(samples, 1):
            print(f"\n{i}. Program: {program}")
            print(f"   Keys: {list(data.keys())}")
            # Look for any feedback field
            for key in data.keys():
                if 'feedback' in key.lower() or 'comment' in key.lower():
                    value = data[key]
                    if value:
                        print(f"   {key}: {str(value)[:100]}...")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"\n✗ Error in JSON structure analysis: {e}")

if __name__ == "__main__":
    analyze_program_feedback()
    check_data_json_structure()