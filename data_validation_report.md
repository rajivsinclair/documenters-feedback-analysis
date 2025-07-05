# Data Validation Report for Documenters Feedback Analysis

## Executive Summary
This report presents the findings from a comprehensive data validation check of the Documenters Feedback Analysis project. The validation examined data consistency across HTML tables, JavaScript charts, CSV files, and JSON data sources.

## 1. Total Feedback Entries Validation

### Finding: **INCONSISTENCY DETECTED**
- **HTML states**: 4,926 feedback entries analyzed
- **CSV All-Time Total**: 5,644 filled feedback entries
- **JSON totals.analyzed_sqlite**: 4,926 entries

**Issue**: There's a discrepancy between the total filled feedback entries (5,644) and the analyzed entries (4,926). This represents 718 entries that were not included in the analysis.

## 2. All-Time Table Validation

### 2.1 Data Accuracy Check
Comparing HTML table against documenters_feedback_stats.csv:

| Program | HTML Entries | CSV Filled | Match? |
|---------|--------------|------------|--------|
| Chicago | 2,032 | 2,032 | ✓ |
| Detroit | 1,190 | 1,190 | ✓ |
| Cleveland | 809 | 809 | ✓ |
| Indianapolis | 248 | 248 | ✓ |
| Minneapolis | 233 | 233 | ✓ |
| Akron | 194 | 194 | ✓ |
| Philadelphia | 188 | 188 | ✓ |
| Atlanta | 149 | 149 | ✓ |
| Omaha | 115 | 115 | ✓ |
| Wichita | 105 | 105 | ✓ |
| San Diego | 92 | 92 | ✓ |
| Dallas | 81 | 81 | ✓ |
| Grand Rapids | 46 | 46 | ✓ |
| Fresno | 34 | 34 | ✓ |
| Bismarck | 21 | 21 | ✓ |
| Los Angeles | 19 | 19 | ✓ |
| Cincinnati | 17 | 17 | ✓ |
| Columbia Gorge | 15 | 15 | ✓ |
| Spokane | 15 | 15 | ✓ |
| Newark | 13 | 13 | ✓ |
| New Brunswick | 13 | 13 | ✓ |
| Fort Worth | 12 | 12 | ✓ |
| Tulsa | 2 | 2 | ✓ |
| Centre County | 1 | 1 | ✓ |

**Result**: ✓ All individual entries match

### 2.2 Percentage Validation
Total from individual entries: 5,644
Percentages all correctly calculated and sum to 100.0%

## 3. Last 12 Months Table Validation

### 3.1 Data Accuracy Check
Comparing HTML table against documenters_feedback_stats.csv:

| Program | HTML Entries | CSV Filled | Match? |
|---------|--------------|------------|--------|
| Detroit | 287 | 287 | ✓ |
| Indianapolis | 166 | 166 | ✓ |
| Chicago | 141 | 141 | ✓ |
| Akron | 129 | 129 | ✓ |
| Cleveland | 96 | 96 | ✓ |
| Wichita | 92 | 92 | ✓ |
| San Diego | 76 | 76 | ✓ |
| Philadelphia | 69 | 69 | ✓ |
| Omaha | 50 | 50 | ✓ |
| Atlanta | 41 | 41 | ✓ |
| Minneapolis | 39 | 39 | ✓ |
| Grand Rapids | 29 | 29 | ✓ |
| Dallas | 28 | 28 | ✓ |
| Bismarck | 20 | 20 | ✓ |
| Los Angeles | 19 | 19 | ✓ |
| Cincinnati | 17 | 17 | ✓ |
| Columbia Gorge | 15 | 15 | ✓ |
| Newark | 13 | 13 | ✓ |
| New Brunswick | 13 | 13 | ✓ |
| Fort Worth | 12 | 12 | ✓ |
| Tulsa | 2 | 2 | ✓ |
| Centre County | 1 | 1 | ✓ |

**Result**: ✓ All individual entries match

### 3.2 Percentage Validation
Total from individual entries: 1,355
Percentages all correctly calculated and sum to 100.1% (due to rounding)

## 4. Program Name Consistency

### Finding: **CONSISTENT**
All program names are consistently spelled and capitalized across:
- HTML tables
- CSV files
- JSON data
- No variations or typos detected

## 5. Chart Data Validation

### 5.1 Cities Chart Data
Comparing chart data (top 10 cities) against actual feedback counts:

| City | Chart Feedback | CSV Feedback | Match? | Issue |
|------|----------------|--------------|--------|-------|
| Chicago | 1,779 | 2,032 | ❌ | -253 |
| Detroit | 1,057 | 1,190 | ❌ | -133 |
| Cleveland | 667 | 809 | ❌ | -142 |
| Indianapolis | 214 | 248 | ❌ | -34 |
| Minneapolis | 205 | 233 | ❌ | -28 |
| Akron | 174 | 194 | ❌ | -20 |
| Philadelphia | 167 | 188 | ❌ | -21 |
| Atlanta | 135 | 149 | ❌ | -14 |
| Omaha | 106 | 115 | ❌ | -9 |
| Wichita | 92 | 105 | ❌ | -13 |

**Finding**: **MAJOR INCONSISTENCY** - The cities chart is displaying lower feedback counts than the actual data. Total shown in chart: 4,596 vs actual top 10: 5,285

### 5.2 Timeline Chart Validation
The timeline chart shows quarterly data totaling approximately 3,039 entries over the displayed period, which doesn't align with either the 4,926 analyzed or 5,644 total feedback entries.

## 6. Data Source Comparison

### PostgreSQL vs CSV Comparison
The postgres_csv_comparison_detailed.csv shows minor discrepancies:
- Most programs match exactly between PostgreSQL and CSV
- Small differences in:
  - Chicago: 4,897 (PG) vs 4,895 (CSV)
  - Cincinnati: 66 (PG) vs 65 (CSV)
  - Columbia Gorge: 38 (PG) vs 37 (CSV)
  - Tulsa: 5 (PG) vs 4 (CSV)

## 7. Missing Data Analysis

### Finding: **DATA GAP IDENTIFIED**
- Total filled feedback: 5,644
- Analyzed feedback: 4,926
- Missing from analysis: 718 entries (12.7%)

This suggests filtering criteria (e.g., >50 characters) excluded valid feedback entries.

## Recommendations

1. **Reconcile Total Counts**: Update the hero section and all references to clearly distinguish between:
   - Total feedback entries collected (5,644)
   - Feedback entries analyzed (4,926)
   - Reason for exclusion (718 entries)

2. **Fix Cities Chart Data**: The chart is showing incorrect, lower values. Update to match the CSV data exactly.

3. **Clarify Timeline Data**: The timeline chart should clearly indicate what subset of data it represents.

4. **Add Data Source Notes**: Include footnotes explaining:
   - Data extraction date
   - Filtering criteria used
   - Any exclusions or limitations

5. **Database Sync**: Investigate and resolve the minor discrepancies between PostgreSQL and CSV exports.

6. **Percentage Precision**: Consider whether to show percentages to one decimal place consistently (current tables show one decimal, matching the CSV).

## Conclusion

While the table data is accurate and consistent with the CSV source, there are significant issues with:
1. The cities chart showing incorrect lower values
2. Unclear representation of which feedback entries were analyzed vs collected
3. Timeline chart data that doesn't clearly map to the stated totals

These issues should be addressed to ensure data transparency and accuracy throughout the visualization.