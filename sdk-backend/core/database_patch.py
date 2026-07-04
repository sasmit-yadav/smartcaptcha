"""
Patch for database.py to add label support for client/demo sessions.
Run this script to apply the patch.
"""

import re

def patch_database_py():
    file_path = 'backend/core/database.py'
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Patch 1: Update function signature
    old_sig = 'def insert_session(session_data: dict, project_id: str = None):'
    new_sig = 'def insert_session(session_data: dict, project_id: str = None, label: str = None):'
    content = content.replace(old_sig, new_sig)
    
    # Patch 2: Update INSERT statement to include label
    # Find the INSERT statement and update it
    old_insert_pattern = r'''INSERT INTO sessions \(
                id, project_id, device_type, screen_width, screen_height,
                user_agent, started_at, webdriver_flag
            \) VALUES \(%s, %s, %s, %s, %s, %s, %s, %s\)
            ON CONFLICT\(id\) DO NOTHING
        \"\"\", \(
            session_data\.get\('sessionId', ''\),
            project_id,
            session_data\.get\('deviceType', 'unknown'\),
            session_data\.get\('screenWidth', 0\),
            session_data\.get\('screenHeight', 0\),
            session_data\.get\('userAgent', ''\),
            start_timestamp,
            session_data\.get\('webdriverFlag', False\),
        \)\)'''
    
    new_insert = '''INSERT INTO sessions (
                id, project_id, device_type, screen_width, screen_height,
                user_agent, started_at, webdriver_flag, label
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT(id) DO NOTHING
        """, (
            session_data.get('sessionId', ''),
            project_id,
            session_data.get('deviceType', 'unknown'),
            session_data.get('screenWidth', 0),
            session_data.get('screenHeight', 0),
            session_data.get('userAgent', ''),
            start_timestamp,
            session_data.get('webdriverFlag', False),
            label,
        ))'''
    
    content = re.sub(old_insert_pattern, new_insert, content, flags=re.MULTILINE | re.DOTALL)
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    print("✅ Patched database.py successfully")

if __name__ == "__main__":
    patch_database_py()
