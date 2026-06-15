"""
Label sessions as 'human' or 'bot' in the database.
Bot sessions are identified by having the same user agent (100 sessions with identical UA).
Human sessions have various different user agents.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from core.database import get_connection, release_connection

load_dotenv(ROOT / "backend" / ".env")


def label_sessions():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # First, reset all labels to NULL
        cursor.execute("UPDATE sessions SET label = NULL")
        print("Reset all session labels")
        
        # Find the user agent with 100 sessions (the bot sessions)
        cursor.execute("""
            SELECT user_agent 
            FROM sessions 
            GROUP BY user_agent 
            HAVING COUNT(*) = 100
        """)
        result = cursor.fetchone()
        
        if result:
            bot_ua = result[0]
            print(f"Found bot user agent: {bot_ua[:80]}...")
            
            # Label bot sessions
            cursor.execute("""
                UPDATE sessions
                SET label = 'bot'
                WHERE user_agent = %s
            """, (bot_ua,))
            bot_count = cursor.rowcount
            print(f"Labeled {bot_count} sessions as 'bot'")
        else:
            print("Could not identify bot user agent")
            bot_count = 0
        
        # Label remaining sessions as human
        cursor.execute("""
            UPDATE sessions
            SET label = 'human'
            WHERE label IS NULL
        """)
        human_count = cursor.rowcount
        print(f"Labeled {human_count} sessions as 'human'")
        
        conn.commit()
        
        # Verify labeling
        cursor.execute("""
            SELECT label, COUNT(*) 
            FROM sessions 
            WHERE label IS NOT NULL
            GROUP BY label
        """)
        results = cursor.fetchall()
        print("\nSession label summary:")
        for label, count in results:
            print(f"  {label}: {count}")
        
        cursor.close()
        
    except Exception as e:
        print(f"Error labeling sessions: {e}")
        conn.rollback()
    finally:
        release_connection(conn)


if __name__ == "__main__":
    label_sessions()
