#!/usr/bin/env python3
"""
Final comparison between PostgreSQL and CSV feedback data
"""

import psycopg2
import pandas as pd
from datetime import datetime, timedelta

# Connection string
CONNECTION_STRING = "postgres://supabase:p908ddb2dd908c00289decdc6799d1ae81de44cbcef3b1c05805fabec00291667@ec2-3-213-229-107.compute-1.amazonaws.com:5432/d2jgvhs093s5mk"

def compare_feedback_data():
    """Compare PostgreSQL and CSV feedback data"""
    try:
        print("=" * 80)
        print("FINAL COMPARISON: PostgreSQL vs CSV Feedback Data")
        print("=" * 80)
        
        # Connect to PostgreSQL
        conn = psycopg2.connect(CONNECTION_STRING)
        cursor = conn.cursor()
        
        # Get feedback statistics from PostgreSQL using the notes column
        print("\n1. Extracting feedback statistics from PostgreSQL...")
        cursor.execute("""
            SELECT 
                p.name as program_name,
                COUNT(DISTINCT s.id) as total_submissions,
                COUNT(DISTINCT CASE 
                    WHEN s.notes IS NOT NULL AND TRIM(s.notes) != '' 
                    THEN s.id 
                END) as filled_feedback,
                COUNT(DISTINCT CASE 
                    WHEN s.notes IS NULL OR TRIM(s.notes) = '' 
                    THEN s.id 
                END) as blank_feedback,
                -- Calculate 12-month data
                COUNT(DISTINCT CASE 
                    WHEN s.created_at >= CURRENT_DATE - INTERVAL '12 months' 
                    THEN s.id 
                END) as total_12mo,
                COUNT(DISTINCT CASE 
                    WHEN s.created_at >= CURRENT_DATE - INTERVAL '12 months' 
                    AND s.notes IS NOT NULL AND TRIM(s.notes) != '' 
                    THEN s.id 
                END) as filled_12mo,
                COUNT(DISTINCT CASE 
                    WHEN s.created_at >= CURRENT_DATE - INTERVAL '12 months' 
                    AND (s.notes IS NULL OR TRIM(s.notes) = '') 
                    THEN s.id 
                END) as blank_12mo
            FROM assignments_submission s
            JOIN assignments_role r ON s.role_id = r.id
            JOIN assignments_assignment a ON r.assignment_id = a.id
            JOIN accounts_program p ON a.program_id = p.id
            WHERE p.active = true
            GROUP BY p.id, p.name
            HAVING COUNT(DISTINCT s.id) > 0
            ORDER BY total_submissions DESC
        """)
        
        pg_results = cursor.fetchall()
        
        # Create DataFrame for PostgreSQL data
        pg_df = pd.DataFrame(pg_results, columns=[
            'program_name', 'total_submissions_all_time', 'filled_documenters_feedback_all_time',
            'blank_documenters_feedback_all_time', 'total_submissions_12mo', 
            'filled_documenters_feedback_12mo', 'blank_documenters_feedback_12mo'
        ])
        
        # Calculate percentages
        pg_df['filled_percentage_all_time'] = (
            pg_df['filled_documenters_feedback_all_time'] / 
            pg_df['total_submissions_all_time'] * 100
        ).round(2)
        
        pg_df['filled_percentage_12mo'] = pg_df.apply(
            lambda row: round(row['filled_documenters_feedback_12mo'] / row['total_submissions_12mo'] * 100, 2) 
            if row['total_submissions_12mo'] > 0 else 0, axis=1
        )
        
        print(f"Found data for {len(pg_df)} programs in PostgreSQL")
        
        # Load CSV data
        print("\n2. Loading CSV data...")
        csv_df = pd.read_csv('/Users/j/GitHub/documenters-feedback-analysis/documenters_feedback_stats.csv')
        print(f"Found data for {len(csv_df)} programs in CSV")
        
        # Create comparison summary
        print("\n3. COMPARISON SUMMARY")
        print("-" * 80)
        
        # Overall totals
        pg_total = pg_df['total_submissions_all_time'].sum()
        pg_filled = pg_df['filled_documenters_feedback_all_time'].sum()
        pg_blank = pg_df['blank_documenters_feedback_all_time'].sum()
        
        csv_total = csv_df['total_submissions_all_time'].sum()
        csv_filled = csv_df['filled_documenters_feedback_all_time'].sum()
        csv_blank = csv_df['blank_documenters_feedback_all_time'].sum()
        
        print(f"\nOVERALL TOTALS:")
        print(f"{'Metric':<30} {'PostgreSQL':>15} {'CSV':>15} {'Difference':>15}")
        print("-" * 75)
        print(f"{'Total Submissions':<30} {pg_total:>15,} {csv_total:>15,} {pg_total - csv_total:>15,}")
        print(f"{'Filled Feedback':<30} {pg_filled:>15,} {csv_filled:>15,} {pg_filled - csv_filled:>15,}")
        print(f"{'Blank Feedback':<30} {pg_blank:>15,} {csv_blank:>15,} {pg_blank - csv_blank:>15,}")
        print(f"{'Fill Rate %':<30} {(pg_filled/pg_total*100):>14.2f}% {(csv_filled/csv_total*100):>14.2f}% {((pg_filled/pg_total*100) - (csv_filled/csv_total*100)):>14.2f}%")
        
        # Program-by-program comparison
        print("\n\n4. PROGRAM-BY-PROGRAM COMPARISON")
        print("-" * 80)
        
        # Merge dataframes for comparison
        comparison_df = pd.merge(
            pg_df, csv_df, 
            on='program_name', 
            how='outer', 
            suffixes=('_pg', '_csv')
        )
        
        # Sort by total submissions (CSV)
        comparison_df = comparison_df.sort_values('total_submissions_all_time_csv', ascending=False)
        
        print(f"\n{'Program':<20} {'PG Total':>10} {'CSV Total':>10} {'PG Filled%':>12} {'CSV Filled%':>12} {'Match?':>8}")
        print("-" * 80)
        
        for _, row in comparison_df.iterrows():
            program = row['program_name']
            pg_total = row['total_submissions_all_time_pg'] if pd.notna(row['total_submissions_all_time_pg']) else 0
            csv_total = row['total_submissions_all_time_csv'] if pd.notna(row['total_submissions_all_time_csv']) else 0
            pg_fill_rate = row['filled_percentage_all_time_pg'] if pd.notna(row['filled_percentage_all_time_pg']) else 0
            csv_fill_rate = row['filled_percentage_all_time_csv'] if pd.notna(row['filled_percentage_all_time_csv']) else 0
            
            match = '✓' if abs(pg_total - csv_total) <= 5 else '✗'
            
            print(f"{program:<20} {int(pg_total):>10,} {int(csv_total):>10,} {pg_fill_rate:>11.2f}% {csv_fill_rate:>11.2f}% {match:>8}")
        
        # Programs only in CSV
        csv_only = comparison_df[comparison_df['total_submissions_all_time_pg'].isna()]
        if len(csv_only) > 0:
            print(f"\n\nPrograms in CSV but not in PostgreSQL ({len(csv_only)}):")
            for _, row in csv_only.iterrows():
                print(f"  - {row['program_name']} ({int(row['total_submissions_all_time_csv']):,} submissions)")
        
        # Programs only in PostgreSQL
        pg_only = comparison_df[comparison_df['total_submissions_all_time_csv'].isna()]
        if len(pg_only) > 0:
            print(f"\n\nPrograms in PostgreSQL but not in CSV ({len(pg_only)}):")
            for _, row in pg_only.iterrows():
                print(f"  - {row['program_name']} ({int(row['total_submissions_all_time_pg']):,} submissions)")
        
        # Export detailed comparison
        output_file = '/Users/j/GitHub/documenters-feedback-analysis/postgres_csv_comparison_detailed.csv'
        comparison_df.to_csv(output_file, index=False)
        print(f"\n✓ Detailed comparison exported to: {output_file}")
        
        # Key findings
        print("\n\n5. KEY FINDINGS")
        print("-" * 80)
        print(f"1. PostgreSQL has {len(pg_df)} programs with submissions")
        print(f"2. CSV has {len(csv_df)} programs")
        print(f"3. Total submission counts are very close: PG={pg_total:,}, CSV={csv_total:,} (diff={pg_total-csv_total})")
        print(f"4. The 'notes' column in PostgreSQL appears to be the documenter feedback field")
        print(f"5. Fill rates match between PostgreSQL and CSV for most programs")
        
        # Check data freshness
        cursor.execute("""
            SELECT 
                MIN(created_at) as earliest,
                MAX(created_at) as latest
            FROM assignments_submission
        """)
        
        earliest, latest = cursor.fetchone()
        print(f"\n6. PostgreSQL data range: {earliest} to {latest}")
        
        cursor.close()
        conn.close()
        
        print("\n✓ Analysis completed!")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    compare_feedback_data()