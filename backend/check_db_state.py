"""
Check current database state - fetch all parameters before testing.
"""

import sys
import os

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(__file__))

from core.database import get_connection, release_connection, get_session_stats
def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

def check_database_state():
    print_section("CURRENT DATABASE STATE")
    
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # Get session stats
        print_section("SESSION STATS")
        stats = get_session_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        # Check sessions table
        print_section("SESSIONS TABLE")
        cursor.execute("SELECT COUNT(*) FROM sessions")
        session_count = cursor.fetchone()[0]
        print(f"  Total sessions: {session_count}")
        
        if session_count > 0:
            cursor.execute("""
                SELECT id, device_type, screen_width, screen_height, 
                       user_agent, started_at, ended_at, event_count, label
                FROM sessions
                ORDER BY created_at DESC
                LIMIT 5
            """)
            sessions = cursor.fetchall()
            print(f"\n  Recent sessions:")
            for sess in sessions:
                print(f"    ID: {sess[0][:8]}...")
                print(f"      Device: {sess[1]}, Screen: {sess[2]}x{sess[3]}")
                print(f"      Started: {sess[4]}, Ended: {sess[5]}")
                print(f"      Events: {sess[6]}, Label: {sess[7]}")
        
        # Check events table
        print_section("EVENTS TABLE")
        cursor.execute("SELECT COUNT(*) FROM events")
        event_count = cursor.fetchone()[0]
        print(f"  Total events: {event_count}")
        
        if event_count > 0:
            # Events by type
            cursor.execute("""
                SELECT event_type, COUNT(*) 
                FROM events 
                GROUP BY event_type 
                ORDER BY COUNT(*) DESC
            """)
            events_by_type = cursor.fetchall()
            print(f"\n  Events by type:")
            for etype, count in events_by_type:
                print(f"    {etype}: {count}")
            
            # Sample mouse events with ML features
            cursor.execute("""
                SELECT event_type, x, y, dist, ang, vel, total_dist
                FROM events 
                WHERE event_type = 'mm'
                LIMIT 3
            """)
            mouse_events = cursor.fetchall()
            if mouse_events:
                print(f"\n  Sample mouse events (ML features):")
                for evt in mouse_events:
                    print(f"    Type: {evt[0]}, Pos: ({evt[1]}, {evt[2]})")
                    print(f"      Dist: {evt[3]}, Ang: {evt[4]}, Vel: {evt[5]}, TotalDist: {evt[6]}")
            
            # Sample scroll events with ML features
            cursor.execute("""
                SELECT event_type, y, scroll_vel, scroll_rev, scroll_pause
                FROM events 
                WHERE event_type = 'sc'
                LIMIT 3
            """)
            scroll_events = cursor.fetchall()
            if scroll_events:
                print(f"\n  Sample scroll events (ML features):")
                for evt in scroll_events:
                    print(f"    Type: {evt[0]}, Y: {evt[1]}")
                    print(f"      Vel: {evt[2]}, Rev: {evt[3]}, Pause: {evt[4]}")
            
            # Sample keyboard events with ML features
            cursor.execute("""
                SELECT event_type, k, iki, hold
                FROM events 
                WHERE event_type IN ('kd', 'ku')
                LIMIT 3
            """)
            key_events = cursor.fetchall()
            if key_events:
                print(f"\n  Sample keyboard events (ML features):")
                for evt in key_events:
                    print(f"    Type: {evt[0]}, Key: {evt[1]}")
                    print(f"      IKI: {evt[2]}, Hold: {evt[3]}")
        
        # Check projects and api_keys tables
        print_section("PROJECTS & API KEYS")
        cursor.execute("SELECT COUNT(*) FROM projects")
        project_count = cursor.fetchone()[0]
        print(f"  Projects: {project_count}")
        
        cursor.execute("SELECT COUNT(*) FROM api_keys")
        apikey_count = cursor.fetchone()[0]
        print(f"  API Keys: {apikey_count}")
        
        print_section("END OF CURRENT STATE")
        
    finally:
        release_connection(conn)

if __name__ == "__main__":
    check_database_state()
