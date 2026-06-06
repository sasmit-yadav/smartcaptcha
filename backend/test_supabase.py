"""
Test Supabase connection and schema.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from core.database import get_connection, release_connection

def test_supabase_connection():
    print("Testing Supabase connection...")
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        print(f"✓ Connected to Supabase")
        print(f"  Version: {version[:80]}...")
        
        # Check if tables exist
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = [row[0] for row in cursor.fetchall()]
        print(f"\n  Tables in database: {tables}")
        
        if not tables:
            print("  ✗ NO TABLES FOUND - Need to run schema creation")
        else:
            print(f"  ✓ Found {len(tables)} tables")
        
        release_connection(conn)
        return True
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_supabase_connection()
