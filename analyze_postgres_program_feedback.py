#!/usr/bin/env python3
"""
Analyze feedback data by program from PostgreSQL
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
        
        # First, let's trace the relationship path
        print("\n1. Exploring the relationship path from feedback to program...")
        
        # Check assignments_role structure
        print("\nChecking assignments_role structure:")
        cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'assignments_role'
            AND (column_name LIKE '%assignment%' OR column_name LIKE '%program%' OR column_name = 'id')
            ORDER BY ordinal_position;
        """)
        
        role_cols = cursor.fetchall()
        for col_name, data_type in role_cols:
            print(f"  - {col_name}: {data_type}")
        
        # Check assignments_assignment structure
        print("\nChecking assignments_assignment structure:")
        cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'assignments_assignment'
            AND (column_name LIKE '%program%' OR column_name LIKE '%agency%' OR column_name = 'id' OR column_name = 'name')
            ORDER BY ordinal_position;
        """)
        
        assignment_cols = cursor.fetchall()
        for col_name, data_type in assignment_cols:
            print(f"  - {col_name}: {data_type}")
        
        # Check if there's a direct program_id in assignment
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' 
            AND table_name = 'assignments_assignment'
            AND column_name = 'program_id'
        """)
        
        has_program_id = cursor.fetchone() is not None
        
        if has_program_id:
            print("\n✓ Found program_id in assignments_assignment table!")
        else:
            print("\n× No direct program_id in assignments_assignment. Checking agency relationship...")
            
            # Check agency structure
            cursor.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'meetings_agency'
                AND (column_name LIKE '%program%' OR column_name = 'id' OR column_name = 'name')
                ORDER BY ordinal_position
                LIMIT 10;
            """)
            
            agency_cols = cursor.fetchall()
            if agency_cols:
                print("\nColumns in meetings_agency:")
                for col_name, data_type in agency_cols:
                    print(f"  - {col_name}: {data_type}")
        
        # Check program table structure
        print("\n2. Exploring program table structure:")
        cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'accounts_program'
            ORDER BY ordinal_position
            LIMIT 15;
        """)
        
        program_cols = cursor.fetchall()
        print("\nColumns in accounts_program:")
        for col_name, data_type in program_cols:
            print(f"  - {col_name}: {data_type}")
        
        # Get sample program data
        print("\n3. Sample program data:")
        cursor.execute("""
            SELECT id, name, location, created_at
            FROM accounts_program
            ORDER BY name
            LIMIT 10
        """)
        
        programs = cursor.fetchall()
        for prog in programs:
            print(f"  ID: {prog[0]}, Name: {prog[1]}, Location: {prog[2]}, Created: {prog[3]}")
        
        # Now let's try to join everything together
        print("\n4. Attempting to join feedback with program information...")
        
        # First, check what we can join
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT af.id) as feedback_count,
                COUNT(DISTINCT r.id) as role_count,
                COUNT(DISTINCT a.id) as assignment_count
            FROM assignments_feedback af
            LEFT JOIN assignments_role r ON af.role_id = r.id
            LEFT JOIN assignments_assignment a ON r.assignment_id = a.id
        """)
        
        counts = cursor.fetchone()
        print(f"\nJoin statistics:")
        print(f"  Feedback records: {counts[0]:,}")
        print(f"  Matched roles: {counts[1]:,}")
        print(f"  Matched assignments: {counts[2]:,}")
        
        # Try to get program statistics
        print("\n5. Calculating feedback statistics by program...")
        
        # Build the appropriate query based on table structure
        if has_program_id:
            query = """
                SELECT 
                    p.name as program_name,
                    p.location as location,
                    COUNT(DISTINCT af.id) as total_feedback,
                    COUNT(DISTINCT CASE WHEN af.comment IS NOT NULL AND TRIM(af.comment) != '' THEN af.id END) as filled_feedback,
                    COUNT(DISTINCT CASE WHEN af.comment IS NULL OR TRIM(af.comment) = '' THEN af.id END) as blank_feedback
                FROM assignments_feedback af
                JOIN assignments_role r ON af.role_id = r.id
                JOIN assignments_assignment a ON r.assignment_id = a.id
                JOIN accounts_program p ON a.program_id = p.id
                GROUP BY p.name, p.location
                ORDER BY total_feedback DESC
            """
        else:
            # Try through agency relationship
            query = """
                SELECT 
                    COALESCE(ag.name, 'Unknown') as program_name,
                    'Via Agency' as location,
                    COUNT(DISTINCT af.id) as total_feedback,
                    COUNT(DISTINCT CASE WHEN af.comment IS NOT NULL AND TRIM(af.comment) != '' THEN af.id END) as filled_feedback,
                    COUNT(DISTINCT CASE WHEN af.comment IS NULL OR TRIM(af.comment) = '' THEN af.id END) as blank_feedback
                FROM assignments_feedback af
                JOIN assignments_role r ON af.role_id = r.id
                JOIN assignments_assignment a ON r.assignment_id = a.id
                LEFT JOIN meetings_agency ag ON a.agency_id = ag.id
                GROUP BY ag.name
                ORDER BY total_feedback DESC
            """
        
        try:
            cursor.execute(query)
            results = cursor.fetchall()
            
            print(f"\nFound feedback data for {len(results)} programs/agencies:")
            
            # Create a nice table
            df_results = pd.DataFrame(results, columns=['Program', 'Location', 'Total', 'Filled', 'Blank'])
            df_results['Fill Rate %'] = (df_results['Filled'] / df_results['Total'] * 100).round(2)
            
            print(df_results.to_string(index=False))
            
            # Calculate totals
            total_feedback = df_results['Total'].sum()
            total_filled = df_results['Filled'].sum()
            total_blank = df_results['Blank'].sum()
            
            print(f"\nOverall totals:")
            print(f"  Total feedback: {total_feedback:,}")
            print(f"  Filled: {total_filled:,}")
            print(f"  Blank: {total_blank:,}")
            print(f"  Overall fill rate: {(total_filled/total_feedback*100):.2f}%")
            
        except Exception as e:
            print(f"Error executing program query: {e}")
            
            # Try a simpler approach
            print("\nTrying alternative approach...")
            cursor.execute("""
                SELECT 
                    a.name as assignment_name,
                    COUNT(DISTINCT af.id) as feedback_count
                FROM assignments_feedback af
                JOIN assignments_role r ON af.role_id = r.id
                JOIN assignments_assignment a ON r.assignment_id = a.id
                GROUP BY a.name
                ORDER BY feedback_count DESC
                LIMIT 20
            """)
            
            alt_results = cursor.fetchall()
            print("\nTop assignments by feedback count:")
            for name, count in alt_results:
                print(f"  {name}: {count:,}")
        
        # Compare with CSV data
        print("\n6. Comparing with CSV data...")
        csv_df = pd.read_csv('/Users/j/GitHub/documenters-feedback-analysis/documenters_feedback_stats.csv')
        
        print(f"\nCSV Summary:")
        print(f"  Programs: {len(csv_df)}")
        print(f"  Total submissions: {csv_df['total_submissions_all_time'].sum():,}")
        print(f"  Total filled: {csv_df['filled_documenters_feedback_all_time'].sum():,}")
        print(f"  Total blank: {csv_df['blank_documenters_feedback_all_time'].sum():,}")
        
        # Check for specific programs in our results
        if len(results) > 0:
            print("\nMatching programs found in both datasets:")
            for _, csv_row in csv_df.head(10).iterrows():
                prog_name = csv_row['program_name']
                # Look for this program in our results
                matching = [r for r in results if prog_name.lower() in str(r[0]).lower()]
                if matching:
                    print(f"  ✓ {prog_name} found in PostgreSQL data")
                else:
                    print(f"  × {prog_name} not found in PostgreSQL data")
        
        cursor.close()
        conn.close()
        print("\n✓ Analysis completed!")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()

def explore_alternative_paths():
    """Explore alternative ways to link feedback to programs"""
    try:
        conn = psycopg2.connect(CONNECTION_STRING)
        cursor = conn.cursor()
        
        print("\n7. Exploring alternative paths to program information...")
        
        # Check if there's a submission table that might help
        print("\nChecking assignments_submission structure:")
        cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'assignments_submission'
            ORDER BY ordinal_position
            LIMIT 15;
        """)
        
        submission_cols = cursor.fetchall()
        for col_name, data_type in submission_cols:
            print(f"  - {col_name}: {data_type}")
        
        # Check for user-program relationships
        print("\nChecking user-program relationships:")
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name LIKE '%user%program%'
            ORDER BY table_name;
        """)
        
        user_program_tables = cursor.fetchall()
        for (table,) in user_program_tables:
            print(f"  - {table}")
        
        # Analyze the actual feedback content
        print("\n8. Analyzing feedback content patterns...")
        cursor.execute("""
            SELECT 
                af.comment,
                r.category,
                a.name as assignment_name
            FROM assignments_feedback af
            JOIN assignments_role r ON af.role_id = r.id
            JOIN assignments_assignment a ON r.assignment_id = a.id
            WHERE af.comment IS NOT NULL 
            AND LENGTH(af.comment) > 10
            LIMIT 5
        """)
        
        sample_feedback = cursor.fetchall()
        print("\nSample feedback with context:")
        for i, (comment, category, assignment) in enumerate(sample_feedback, 1):
            print(f"\n{i}. Assignment: {assignment}")
            print(f"   Category: {category}")
            print(f"   Feedback preview: {comment[:100]}...")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"\n✗ Error in alternative exploration: {e}")

if __name__ == "__main__":
    analyze_program_feedback()
    explore_alternative_paths()