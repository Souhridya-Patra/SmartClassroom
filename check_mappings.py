import os
import mysql.connector

# Connect to timetable_db
conn = mysql.connector.connect(
    host=os.getenv('TIMETABLE_DB_HOST', 'host.docker.internal'),
    port=int(os.getenv('TIMETABLE_DB_PORT', '3306')),
    user=os.getenv('TIMETABLE_DB_USER', 'root'),
    password=os.getenv('TIMETABLE_DB_PASSWORD', ''),
    database=os.getenv('TIMETABLE_DB_NAME', 'timetable_db')
)
cur = conn.cursor(dictionary=True)

# Get mapping data
cur.execute('SELECT smart_class_id, section_id FROM smartclassroom_class_section_map WHERE is_active = 1')
mappings = cur.fetchall()
print('SmartClassroom Class ↔ Section Mappings:')
for m in mappings:
    print(f"  {m['smart_class_id']} → section_id {m['section_id']}")

# Get room assignments
print('\nTimetable Room Assignments (today/this slot):')
cur.execute('''
    SELECT DISTINCT r.name as room_name, s.name as section_name, s.id as section_id
    FROM timetable t
    JOIN rooms r ON t.room_id = r.id
    JOIN sections s ON t.section_id = s.id
    LIMIT 5
''')
rooms = cur.fetchall()
if rooms:
    for r in rooms:
        print(f"  Room: {r['room_name']} (section_id: {r['section_id']}, section_name: {r['section_name']})")
else:
    print("  (no timetable entries found)")

cur.close()
conn.close()
