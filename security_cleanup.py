#!/usr/bin/env python3
"""
Security cleanup script to remove hardcoded credentials and create secure environment configuration
"""

import os
import glob
import re
from pathlib import Path

# Files to check for hardcoded credentials
FILES_TO_CHECK = [
    "test_postgres_connection.py",
    "final_postgres_csv_comparison.py", 
    "analyze_postgres_program_feedback_fixed.py",
    "analyze_postgres_program_feedback.py",
    "analyze_postgres_feedback.py"
]

# Pattern to match PostgreSQL connection strings
CONNECTION_PATTERN = re.compile(
    r'postgres(?:ql)?://[^:]+:[^@]+@[^/]+/[^\s"\'"]+', 
    re.IGNORECASE
)

def main():
    """Main cleanup function"""
    print("🔒 Security Cleanup Script")
    print("=" * 60)
    
    removed_files = []
    current_dir = Path.cwd()
    
    # Step 1: Remove files with hardcoded credentials
    print("\n📁 Checking for files with hardcoded credentials...")
    
    for filename in FILES_TO_CHECK:
        filepath = current_dir / filename
        if filepath.exists():
            try:
                with open(filepath, 'r') as f:
                    content = f.read()
                    if CONNECTION_PATTERN.search(content):
                        print(f"  ⚠️  Found hardcoded credentials in: {filename}")
                        os.remove(filepath)
                        removed_files.append(str(filepath))
                        print(f"  ✅ Removed: {filename}")
            except Exception as e:
                print(f"  ❌ Error checking {filename}: {e}")
    
    # Step 2: Create .env.example file
    print("\n📝 Creating .env.example file...")
    env_example_content = """# PostgreSQL Database Configuration
# Copy this file to .env and fill in your actual values

# Database connection string
DATABASE_URL=postgres://username:password@host:port/database

# Alternative individual components (if not using connection string)
POSTGRES_HOST=your-host-here
POSTGRES_PORT=5432
POSTGRES_DATABASE=your-database-name
POSTGRES_USER=your-username
POSTGRES_PASSWORD=your-password

# Optional SSL configuration
POSTGRES_SSL_MODE=require
"""
    
    env_example_path = current_dir / ".env.example"
    with open(env_example_path, 'w') as f:
        f.write(env_example_content)
    print(f"  ✅ Created: .env.example")
    
    # Step 3: Update .gitignore
    print("\n🚫 Updating .gitignore...")
    gitignore_path = current_dir / ".gitignore"
    
    # Patterns to ensure are in .gitignore
    env_patterns = [
        ".env",
        ".env.*",
        "!.env.example",
        "*.env",
        "local.env",
        "production.env"
    ]
    
    existing_patterns = set()
    if gitignore_path.exists():
        with open(gitignore_path, 'r') as f:
            existing_patterns = set(line.strip() for line in f if line.strip() and not line.startswith('#'))
    
    # Add missing patterns
    patterns_to_add = []
    for pattern in env_patterns:
        if pattern not in existing_patterns:
            patterns_to_add.append(pattern)
    
    if patterns_to_add:
        with open(gitignore_path, 'a') as f:
            if gitignore_path.stat().st_size > 0:
                f.write("\n")
            f.write("# Environment files\n")
            for pattern in patterns_to_add:
                f.write(f"{pattern}\n")
        print(f"  ✅ Added {len(patterns_to_add)} patterns to .gitignore")
    else:
        print("  ℹ️  .gitignore already contains all necessary patterns")
    
    # Step 4: Summary report
    print("\n📊 Security Cleanup Summary")
    print("=" * 60)
    print(f"\n🗑️  Files removed for security reasons ({len(removed_files)} total):")
    
    if removed_files:
        for file in removed_files:
            print(f"  - {os.path.basename(file)}")
    else:
        print("  - No files needed to be removed")
    
    print("\n✅ Security cleanup completed!")
    print("\n📌 Next steps:")
    print("  1. Copy .env.example to .env")
    print("  2. Fill in your actual database credentials in .env")
    print("  3. Update your Python scripts to use environment variables:")
    print("     import os")
    print("     from dotenv import load_dotenv")
    print("     load_dotenv()")
    print("     DATABASE_URL = os.getenv('DATABASE_URL')")
    print("\n  4. Install python-dotenv if not already installed:")
    print("     pip install python-dotenv")

if __name__ == "__main__":
    main()