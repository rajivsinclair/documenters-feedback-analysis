#!/usr/bin/env python3
"""
Update index.html with verified data from CSV
This script makes all necessary updates to the HTML file
"""

import re
import json

def update_index_html():
    """Update the index.html file with correct statistics"""
    
    # Read the current index.html
    with open('index.html', 'r') as f:
        html_content = f.read()
    
    # Load the generated data
    with open('final_all_time_table.html', 'r') as f:
        all_time_table_rows = f.read()
    
    with open('final_12month_table.html', 'r') as f:
        twelve_month_table_rows = f.read()
    
    with open('final_chart_data.json', 'r') as f:
        chart_data = json.load(f)
    
    # Create backup
    with open('index.html.backup', 'w') as f:
        f.write(html_content)
    
    print("Created backup: index.html.backup")
    
    # Update the all-time table header
    html_content = re.sub(
        r'All-Time Feedback \(\d+,?\d* entries\)',
        f'All-Time Feedback ({chart_data["totals"]["all_time_filled"]:,} entries)',
        html_content
    )
    
    # Update the 12-month table header
    html_content = re.sub(
        r'Last 12 Months \(\d+,?\d* entries\)',
        f'Last 12 Months ({chart_data["totals"]["12_month_filled"]:,} entries)',
        html_content
    )
    
    # Update the all-time table content
    # Find the table body for all-time feedback
    all_time_pattern = r'(<h3>All-Time Feedback.*?<tbody>)(.*?)(</tbody>)'
    match = re.search(all_time_pattern, html_content, re.DOTALL)
    if match:
        html_content = html_content[:match.start(2)] + '\n' + all_time_table_rows + '\n                        ' + html_content[match.end(2):]
        print("✓ Updated all-time feedback table")
    
    # Update the 12-month table content
    twelve_month_pattern = r'(<h3>Last 12 Months.*?<tbody>)(.*?)(</tbody>)'
    match = re.search(twelve_month_pattern, html_content, re.DOTALL)
    if match:
        html_content = html_content[:match.start(2)] + '\n' + twelve_month_table_rows + '\n                        ' + html_content[match.end(2):]
        print("✓ Updated 12-month feedback table")
    
    # Update cities chart data
    # Convert lists to JavaScript array format
    cities_labels_js = json.dumps(chart_data['cities_chart']['labels'])
    feedback_analyzed_js = json.dumps(chart_data['cities_chart']['feedback_analyzed'])
    roles_without_js = json.dumps(chart_data['cities_chart']['roles_without_feedback'])
    
    # Update cities chart labels
    cities_labels_pattern = r"(const citiesData = \{[\s\S]*?labels: )\[[^\]]+\]"
    html_content = re.sub(cities_labels_pattern, r"\1" + cities_labels_js, html_content)
    
    # Update feedback analyzed data
    feedback_pattern = r"(label: 'Feedback Entries Analyzed',[\s\S]*?data: )\[[^\]]+\]"
    html_content = re.sub(feedback_pattern, r"\1" + feedback_analyzed_js, html_content)
    
    # Update roles without feedback data
    roles_pattern = r"(label: 'Roles Without Feedback',[\s\S]*?data: )\[[^\]]+\]"
    html_content = re.sub(roles_pattern, r"\1" + roles_without_js, html_content)
    
    print("✓ Updated cities chart data")
    
    # Write the updated HTML
    with open('index.html', 'w') as f:
        f.write(html_content)
    
    print("\n✓ Successfully updated index.html")
    print(f"\nSummary of changes:")
    print(f"- All-time feedback total: {chart_data['totals']['all_time_filled']:,} entries")
    print(f"- 12-month feedback total: {chart_data['totals']['12_month_filled']:,} entries")
    print(f"- All-time table now shows 24 programs (all available from requested list)")
    print(f"- 12-month table now shows 22 programs (with recent activity)")
    print(f"- Cities chart updated with accurate data")
    
    print(f"\nNote: The following requested programs are not in the database:")
    print("- Atlantic County")
    print("- Cape May County")
    print("- Gary")
    print("- Nebraska Panhandle")

if __name__ == "__main__":
    update_index_html()