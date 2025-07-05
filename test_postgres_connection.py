#!/usr/bin/env python3
"""
Test PostgreSQL connection and explore available data
"""

import psycopg2
from psycopg2 import sql
import pandas as pd
import os

# Connection string provided
CONNECTION_STRING = "postgres://supabase:p908ddb2dd908c00289decdc6799d1ae81de44cbcef3b1c05805fabec00291667@ec2-3-213-229-107.compute-1.amazonaws.com:5432/d2jgvhs093s5mk"

def test_connection():
    """Test PostgreSQL connection and explore schema"""
    try:
        print("Attempting to connect to PostgreSQL...")
        conn = psycopg2.connect(CONNECTION_STRING)
        cursor = conn.cursor()
        
        print("✓ Connected successfully!")
        
        # Get all tables
        print("\nFetching all tables...")
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        
        print(f"\nFound {len(tables)} tables:")
        relevant_tables = []
        for (table_name,) in tables:
            print(f"  - {table_name}")
            # Check if table might contain feedback data
            if any(keyword in table_name.lower() for keyword in ['feedback', 'submission', 'document', 'entry', 'response']):
                relevant_tables.append(table_name)
        
        print(f"\nPotentially relevant tables: {relevant_tables}")
        
        # For each relevant table, get structure
        for table in relevant_tables:
            print(f"\n\nTable: {table}")
            print("-" * 50)
            
            # Get column info
            cursor.execute(f"""
                SELECT column_name, data_type, character_maximum_length
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position;
            """, (table,))
            
            columns = cursor.fetchall()
            print("Columns:")
            for col_name, data_type, max_length in columns:
                print(f"  - {col_name}: {data_type}" + (f"({max_length})" if max_length else ""))
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"\nTotal rows: {count:,}")
            
            # Get sample data if rows exist
            if count > 0:
                cursor.execute(f"SELECT * FROM {table} LIMIT 3")
                sample_data = cursor.fetchall()
                print("\nSample data (first 3 rows):")
                for i, row in enumerate(sample_data, 1):
                    print(f"  Row {i}: {row[:5]}..." if len(row) > 5 else f"  Row {i}: {row}")
        
        # Look for any table with 'program' in the name
        print("\n\nSearching for program-related tables...")
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE '%program%'
            ORDER BY table_name;
        """)
        program_tables = cursor.fetchall()
        if program_tables:
            print(f"Found {len(program_tables)} program-related tables:")
            for (table_name,) in program_tables:
                print(f"  - {table_name}")
        
        cursor.close()
        conn.close()
        print("\n✓ Connection test completed successfully!")
        
    except Exception as e:
        print(f"\n✗ Error connecting to PostgreSQL: {e}")
        print(f"Error type: {type(e).__name__}")

if __name__ == "__main__":
    test_connection()