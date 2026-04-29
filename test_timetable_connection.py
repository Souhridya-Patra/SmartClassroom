import mysql.connector
import os

# Use the same config as timetable service
DB_CONFIG = {
    "host":     os.getenv("TIMETABLE_DB_HOST", os.getenv("DB_HOST", "localhost")),
    "port":     int(os.getenv("TIMETABLE_DB_PORT", os.getenv("DB_PORT", "3306"))),
    "user":     os.getenv("TIMETABLE_DB_USER", os.getenv("DB_USER", "root")),
    "password": os.getenv("TIMETABLE_DB_PASSWORD", os.getenv("DB_PASSWORD", "")),
    "database": os.getenv("TIMETABLE_DB_NAME", os.getenv("DB_NAME", "timetable_db"))
}

try:
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute('SELECT @@hostname')
    hostname = cursor.fetchone()[0]
    print(f'Connected to: {hostname}')
    cursor.execute('SHOW TABLES LIKE "smartclassroom_class_section_map"')
    tables = cursor.fetchall()
    print(f'Table exists: {bool(tables)}')
    if tables:
        cursor.execute('SELECT COUNT(*) FROM smartclassroom_class_section_map')
        count = cursor.fetchone()[0]
        print(f'Rows in mapping table: {count}')
    else:
        print('Tables in database:')
        cursor.execute('SHOW TABLES')
        all_tables = cursor.fetchall()
        for t in all_tables[:5]:
            print(f'  - {t[0]}')
        if len(all_tables) > 5:
            print(f'  ... and {len(all_tables)-5} more')
    cursor.close()
    conn.close()
except Exception as e:
    print(f'Error: {e}')
