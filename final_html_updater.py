#!/usr/bin/env python3
"""
Final HTML updater - generates updated HTML content based on verified CSV data
This script creates the exact HTML snippets needed to update index.html
"""

import pandas as pd
import json
from datetime import datetime

# List of all requested programs
REQUESTED_PROGRAMS = [
    "Akron", "Atlanta", "Atlantic County", "Bismarck", "Cape May County",
    "Centre County", "Chicago", "Cincinnati", "Cleveland", "Columbia Gorge",
    "Dallas", "Detroit", "Fort Worth", "Fresno", "Gary",
    "Grand Rapids", "Indianapolis", "Los Angeles", "Minneapolis", 
    "Nebraska Panhandle", "New Brunswick", "Newark", "Omaha", "Philadelphia",
    "San Diego", "Spokane", "Tulsa", "Wichita"
]

def generate_final_report():
    """Generate final HTML updates and report"""
    
    # Load CSV data
    df = pd.read_csv('documenters_feedback_stats.csv')
    
    # Load SQLite counts for accurate chart data
    import sqlite3
    conn = sqlite3.connect('feedback_analysis.db')
    sqlite_query = """
    SELECT program_name, COUNT(*) as feedback_count
    FROM feedback_embeddings
    GROUP BY program_name
    """
    sqlite_df = pd.read_sql_query(sqlite_query, conn)
    sqlite_counts = dict(zip(sqlite_df['program_name'], sqlite_df['feedback_count']))
    conn.close()
    
    # Check which requested programs exist in data
    existing_programs = set(df['program_name'].values)
    missing_programs = [p for p in REQUESTED_PROGRAMS if p not in existing_programs]
    available_programs = [p for p in REQUESTED_PROGRAMS if p in existing_programs]
    
    print("=== FINAL HTML UPDATE REPORT ===")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\nPrograms Status:")
    print(f"- Requested programs: {len(REQUESTED_PROGRAMS)}")
    print(f"- Available in data: {len(available_programs)}")
    print(f"- Missing: {len(missing_programs)} ({', '.join(missing_programs)})")
    
    # Generate ALL-TIME table
    print("\n\n=== ALL-TIME FEEDBACK TABLE ===")
    print("This table will include ALL requested programs that have data:")
    
    # Filter and sort for all-time table
    df_all_time = df[df['program_name'].isin(available_programs)].copy()
    df_all_time = df_all_time.sort_values('filled_documenters_feedback_all_time', ascending=False)
    
    # Calculate total for accurate percentages
    total_filled_all_time = df_all_time['filled_documenters_feedback_all_time'].sum()
    
    all_time_rows = []
    print(f"\nTotal filled feedback (all programs): {total_filled_all_time:,}")
    print("\nProgram | Filled Feedback | Percentage")
    print("-" * 50)
    
    for _, row in df_all_time.iterrows():
        filled = row['filled_documenters_feedback_all_time']
        pct = (filled / total_filled_all_time * 100) if total_filled_all_time > 0 else 0
        print(f"{row['program_name']:<20} | {filled:>8,} | {pct:>6.1f}%")
        
        all_time_rows.append(f"""                            <tr>
                                <td>{row['program_name']}</td>
                                <td>{filled:,}</td>
                                <td>{pct:.1f}%</td>
                            </tr>""")
    
    # Generate 12-MONTH table
    print("\n\n=== LAST 12 MONTHS TABLE ===")
    print("This table includes programs with 12-month data:")
    
    # Filter for programs with 12-month data
    df_12mo = df[(df['program_name'].isin(available_programs)) & 
                 (df['total_submissions_12mo'] > 0)].copy()
    df_12mo = df_12mo.sort_values('filled_documenters_feedback_12mo', ascending=False)
    
    total_filled_12mo = df_12mo['filled_documenters_feedback_12mo'].sum()
    
    twelve_mo_rows = []
    print(f"\nTotal filled feedback (12 months): {total_filled_12mo:,}")
    print("\nProgram | Filled Feedback | Percentage")
    print("-" * 50)
    
    for _, row in df_12mo.iterrows():
        filled = row['filled_documenters_feedback_12mo']
        pct = (filled / total_filled_12mo * 100) if total_filled_12mo > 0 else 0
        print(f"{row['program_name']:<20} | {filled:>8,} | {pct:>6.1f}%")
        
        twelve_mo_rows.append(f"""                            <tr>
                                <td>{row['program_name']}</td>
                                <td>{filled:,}</td>
                                <td>{pct:.1f}%</td>
                            </tr>""")
    
    # Generate cities chart data (top 10 by filled feedback)
    print("\n\n=== CITIES CHART DATA ===")
    df_chart = df[df['program_name'].isin(available_programs)].copy()
    df_chart = df_chart.sort_values('filled_documenters_feedback_all_time', ascending=False).head(10)
    
    cities_labels = []
    feedback_analyzed = []
    roles_without_feedback = []
    
    print("\nCity | Analyzed (SQLite) | Blank Submissions")
    print("-" * 50)
    
    for _, row in df_chart.iterrows():
        program = row['program_name']
        analyzed = sqlite_counts.get(program, row['filled_documenters_feedback_all_time'])
        blank = row['blank_documenters_feedback_all_time']
        
        cities_labels.append(program)
        feedback_analyzed.append(analyzed)
        roles_without_feedback.append(blank)
        
        print(f"{program:<20} | {analyzed:>8,} | {blank:>8,}")
    
    # Save all generated content
    with open('final_all_time_table.html', 'w') as f:
        f.write('\n'.join(all_time_rows))
    
    with open('final_12month_table.html', 'w') as f:
        f.write('\n'.join(twelve_mo_rows))
    
    # Generate the complete data for charts
    chart_data = {
        'cities_chart': {
            'labels': cities_labels,
            'feedback_analyzed': feedback_analyzed,
            'roles_without_feedback': roles_without_feedback
        },
        'totals': {
            'all_time_filled': int(total_filled_all_time),
            '12_month_filled': int(total_filled_12mo),
            'analyzed_sqlite': sum(sqlite_counts.values())
        }
    }
    
    with open('final_chart_data.json', 'w') as f:
        json.dump(chart_data, f, indent=2)
    
    # Generate update instructions
    print("\n\n=== UPDATE INSTRUCTIONS ===")
    print(f"1. Total count remains: {sum(sqlite_counts.values()):,}")
    print(f"2. All-time table header: All-Time Feedback ({total_filled_all_time:,} entries)")
    print(f"3. 12-month table header: Last 12 Months ({total_filled_12mo:,} entries)")
    print(f"4. All-time table shows: {len(all_time_rows)} programs")
    print(f"5. 12-month table shows: {len(twelve_mo_rows)} programs")
    print(f"6. Cities chart shows top: {len(cities_labels)} programs")
    
    print("\n\nGenerated files:")
    print("- final_all_time_table.html")
    print("- final_12month_table.html") 
    print("- final_chart_data.json")
    
    return chart_data

if __name__ == "__main__":
    chart_data = generate_final_report()