import mysql.connector
from mysql.connector import Error
import os

try:
    # Try using environment variables first, then fall back to defaults
    host = os.getenv('DB_HOST', 'host.docker.internal')
    port = int(os.getenv('DB_PORT', 3306))
    user = os.getenv('DB_USER', 'root')
    password = os.getenv('DB_PASSWORD', 'root')
    database = os.getenv('DB_NAME', 'smart_classroom')
    
    print(f"Connecting to {host}:{port} as {user}...")
    
    conn = mysql.connector.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database
    )
    cursor = conn.cursor()
    
    # Add columns
    try:
        cursor.execute("ALTER TABLE class_sessions ADD COLUMN period_id BIGINT NULL")
        print("✓ Added period_id column")
    except Error as e:
        if "already exists" in str(e).lower() or "Duplicate column" in str(e):
            print("✓ period_id column already exists")
        else:
            print(f"Error adding period_id: {e}")
    
    try:
        cursor.execute("ALTER TABLE class_sessions ADD COLUMN timetable_schedule_id BIGINT NULL")
        print("✓ Added timetable_schedule_id column")
    except Error as e:
        if "already exists" in str(e).lower() or "Duplicate column" in str(e):
            print("✓ timetable_schedule_id column already exists")
        else:
            print(f"Error adding timetable_schedule_id: {e}")
    
    conn.commit()
    
    # Verify columns
    cursor.execute("DESCRIBE class_sessions")
    cols = [row[0] for row in cursor.fetchall()]
    print(f"\nFinal columns: {sorted(cols)}")
    
    cursor.close()
    conn.close()
except Error as e:
    print(f"Connection error: {e}")
