#!/usr/bin/env python3
"""
Example of secure database connection using environment variables
"""

import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_database_connection():
    """
    Create a secure database connection using environment variables
    """
    # Option 1: Use full connection string
    database_url = os.getenv('DATABASE_URL')
    
    if database_url:
        return psycopg2.connect(database_url)
    
    # Option 2: Use individual components
    connection_params = {
        'host': os.getenv('POSTGRES_HOST'),
        'port': os.getenv('POSTGRES_PORT', '5432'),
        'database': os.getenv('POSTGRES_DATABASE'),
        'user': os.getenv('POSTGRES_USER'),
        'password': os.getenv('POSTGRES_PASSWORD')
    }
    
    # Add SSL if configured
    ssl_mode = os.getenv('POSTGRES_SSL_MODE')
    if ssl_mode:
        connection_params['sslmode'] = ssl_mode
    
    # Check for required parameters
    required = ['host', 'database', 'user', 'password']
    missing = [param for param in required if not connection_params.get(param)]
    
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    
    return psycopg2.connect(**connection_params)

def test_connection():
    """Test the database connection"""
    try:
        print("Attempting to connect to database...")
        conn = get_database_connection()
        cursor = conn.cursor()
        
        # Test query
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"✅ Connected successfully!")
        print(f"PostgreSQL version: {version[0]}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nMake sure you have:")
        print("1. Created a .env file (copy from .env.example)")
        print("2. Filled in your actual database credentials")
        print("3. Installed python-dotenv: pip install python-dotenv")

if __name__ == "__main__":
    test_connection()