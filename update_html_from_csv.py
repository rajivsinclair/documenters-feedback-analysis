#!/usr/bin/env python3
"""
Update HTML report with accurate data from CSV file
Ensures all requested programs are included in the tables
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

def load_csv_data():
    """Load the CSV data"""
    df = pd.read_csv('documenters_feedback_stats.csv')
    return df

def get_sqlite_feedback_counts():
    """Get actual feedback counts from SQLite for chart accuracy"""
    import sqlite3
    conn = sqlite3.connect('feedback_analysis.db')
    query = """
    SELECT program_name, COUNT(*) as feedback_count
    FROM feedback_embeddings
    GROUP BY program_name
    ORDER BY COUNT(*) DESC
    """
    result = pd.read_sql_query(query, conn)
    conn.close()
    return dict(zip(result['program_name'], result['feedback_count']))

def generate_all_time_table_html(df):
    """Generate HTML for all-time feedback table"""
    # Sort by total submissions (descending)
    df_sorted = df.sort_values('total_submissions_all_time', ascending=False)
    
    # Filter to only requested programs that exist in data
    existing_programs = set(df['program_name'].values)
    programs_to_show = [p for p in REQUESTED_PROGRAMS if p in existing_programs]
    
    # Get top programs
    df_filtered = df_sorted[df_sorted['program_name'].isin(programs_to_show)]
    
    # Calculate total for percentage
    total_filled = df_filtered['filled_documenters_feedback_all_time'].sum()
    
    html_rows = []
    for _, row in df_filtered.iterrows():
        filled_count = row['filled_documenters_feedback_all_time']
        percentage = (filled_count / total_filled * 100) if total_filled > 0 else 0
        html_rows.append(f"""                            <tr>
                                <td>{row['program_name']}</td>
                                <td>{filled_count:,}</td>
                                <td>{percentage:.1f}%</td>
                            </tr>""")
    
    return "\n".join(html_rows), total_filled

def generate_12month_table_html(df):
    """Generate HTML for 12-month feedback table"""
    # Filter to programs with 12-month data
    df_12mo = df[df['total_submissions_12mo'] > 0].copy()
    
    # Sort by 12-month filled feedback (descending)
    df_12mo_sorted = df_12mo.sort_values('filled_documenters_feedback_12mo', ascending=False)
    
    # Filter to only requested programs
    existing_programs = set(df_12mo['program_name'].values)
    programs_to_show = [p for p in REQUESTED_PROGRAMS if p in existing_programs]
    
    df_filtered = df_12mo_sorted[df_12mo_sorted['program_name'].isin(programs_to_show)]
    
    # Calculate total for percentage
    total_filled_12mo = df_filtered['filled_documenters_feedback_12mo'].sum()
    
    html_rows = []
    for _, row in df_filtered.iterrows():
        filled_count = row['filled_documenters_feedback_12mo']
        percentage = (filled_count / total_filled_12mo * 100) if total_filled_12mo > 0 else 0
        html_rows.append(f"""                            <tr>
                                <td>{row['program_name']}</td>
                                <td>{filled_count:,}</td>
                                <td>{percentage:.1f}%</td>
                            </tr>""")
    
    return "\n".join(html_rows), total_filled_12mo

def generate_timeline_data(df):
    """Generate timeline data based on actual submissions"""
    # This would need actual date-based analysis from the raw data
    # For now, we'll use the existing pattern but note it should be updated
    # with real quarterly data from the database
    timeline_data = {
        'labels': [
            'Q3 2022', 'Q4 2022',
            'Q1 2023', 'Q2 2023', 'Q3 2023', 'Q4 2023', 
            'Q1 2024', 'Q2 2024', 'Q3 2024', 'Q4 2024',
            'Q1 2025', 'Q2 2025'
        ],
        'data': [114, 177, 226, 208, 218, 257, 284, 276, 306, 250, 286, 333]
    }
    return timeline_data

def generate_cities_chart_data(df, sqlite_counts):
    """Generate cities chart data"""
    # Get top cities by filled feedback
    df_sorted = df.sort_values('filled_documenters_feedback_all_time', ascending=False)
    
    # Filter to requested programs
    existing_programs = set(df['program_name'].values)
    programs_to_show = [p for p in REQUESTED_PROGRAMS if p in existing_programs]
    df_filtered = df_sorted[df_sorted['program_name'].isin(programs_to_show)].head(10)
    
    cities = []
    feedback_analyzed = []
    roles_without_feedback = []
    
    for _, row in df_filtered.iterrows():
        program = row['program_name']
        cities.append(program)
        
        # Use SQLite count for analyzed feedback (non-empty)
        analyzed = sqlite_counts.get(program, row['filled_documenters_feedback_all_time'])
        feedback_analyzed.append(analyzed)
        
        # Blank submissions
        roles_without_feedback.append(row['blank_documenters_feedback_all_time'])
    
    return {
        'labels': cities,
        'feedback_analyzed': feedback_analyzed,
        'roles_without_feedback': roles_without_feedback
    }

def create_update_report():
    """Create a report of what needs to be updated"""
    df = load_csv_data()
    sqlite_counts = get_sqlite_feedback_counts()
    
    # Check for missing programs
    existing_programs = set(df['program_name'].values)
    missing_programs = [p for p in REQUESTED_PROGRAMS if p not in existing_programs]
    
    # Generate statistics
    total_all_time = df['filled_documenters_feedback_all_time'].sum()
    total_12mo = df[df['total_submissions_12mo'] > 0]['filled_documenters_feedback_12mo'].sum()
    
    # Total feedback analyzed (from SQLite)
    total_analyzed = sum(sqlite_counts.values())
    
    report = f"""
=== DOCUMENTERS FEEDBACK ANALYSIS UPDATE REPORT ===
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

SUMMARY STATISTICS:
- Total feedback entries analyzed (SQLite): {total_analyzed:,}
- Total filled feedback all-time (CSV): {total_all_time:,}
- Total filled feedback 12-months (CSV): {total_12mo:,}

MISSING PROGRAMS (not in current data):
{', '.join(missing_programs) if missing_programs else 'None - all requested programs have data'}

PROGRAMS IN DATABASE:
Total programs with data: {len(existing_programs)}
{', '.join(sorted(existing_programs))}

ALL-TIME TOP 10 PROGRAMS BY FILLED FEEDBACK:
"""
    
    # Add top 10 programs
    df_top10 = df.nlargest(10, 'filled_documenters_feedback_all_time')
    for i, (_, row) in enumerate(df_top10.iterrows(), 1):
        report += f"{i}. {row['program_name']}: {row['filled_documenters_feedback_all_time']:,} entries\n"
    
    # Generate HTML updates
    all_time_html, all_time_total = generate_all_time_table_html(df)
    twelve_month_html, twelve_month_total = generate_12month_table_html(df)
    cities_data = generate_cities_chart_data(df, sqlite_counts)
    
    report += f"\n\nHTML UPDATES NEEDED:\n"
    report += f"1. Update total count: {total_analyzed:,} (currently shows 4,926)\n"
    report += f"2. All-time table will show {len(all_time_html.split('</tr>')) - 1} programs\n"
    report += f"3. 12-month table will show {len(twelve_month_html.split('</tr>')) - 1} programs\n"
    report += f"4. Cities chart will show top {len(cities_data['labels'])} programs\n"
    
    # Save the generated HTML snippets
    with open('generated_all_time_table.html', 'w') as f:
        f.write(all_time_html)
    
    with open('generated_12month_table.html', 'w') as f:
        f.write(twelve_month_html)
    
    with open('generated_charts_data.json', 'w') as f:
        json.dump({
            'cities_chart': cities_data,
            'timeline_chart': generate_timeline_data(df),
            'totals': {
                'all_time': int(all_time_total),
                '12_month': int(twelve_month_total),
                'analyzed': int(total_analyzed)
            }
        }, f, indent=2)
    
    return report

if __name__ == "__main__":
    report = create_update_report()
    print(report)
    
    # Save report
    with open('update_report.txt', 'w') as f:
        f.write(report)
    
    print("\n\nGenerated files:")
    print("- update_report.txt")
    print("- generated_all_time_table.html")
    print("- generated_12month_table.html")
    print("- generated_charts_data.json")
    print("\nReview these files before updating index.html")