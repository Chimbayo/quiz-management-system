#!/usr/bin/env python3
"""
Test script to verify database connectivity and basic functionality
"""

import os
from dotenv import load_dotenv
import psycopg2

def test_database_connection():
    """Test database connection"""
    load_dotenv()
    
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            database=os.getenv('DB_NAME', 'quiz_db'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'password'),
            port=os.getenv('DB_PORT', '5432')
        )
        
        print("✅ Database connection successful!")
        
        # Test basic query
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()
        print(f"📊 PostgreSQL version: {version[0]}")
        
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("\n🔧 Troubleshooting tips:")
        print("1. Make sure PostgreSQL is running")
        print("2. Check your .env file configuration")
        print("3. Verify database credentials")
        print("4. Ensure database 'quiz_db' exists")
        return False

def test_flask_app():
    """Test Flask app import"""
    try:
        from app import app
        print("✅ Flask app imports successfully!")
        return True
    except Exception as e:
        print(f"❌ Flask app import failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Quiz Management System...\n")
    
    # Test Flask app
    flask_ok = test_flask_app()
    print()
    
    # Test database
    db_ok = test_database_connection()
    print()
    
    if flask_ok and db_ok:
        print("🎉 All tests passed! You can now run the application with:")
        print("   python app.py")
    else:
        print("⚠️  Some tests failed. Please fix the issues before running the app.")
