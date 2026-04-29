import os
import mysql.connector

conn = mysql.connector.connect(
    host=os.getenv('DB_HOST'),
    port=int(os.getenv('DB_PORT')),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    database=os.getenv('DB_NAME')
)
cur = conn.cursor()
cur.execute('SELECT class_id, class_name, section, semester FROM classes WHERE class_id LIKE "TEST-WAMP-%" ORDER BY class_id DESC LIMIT 1')
result = cur.fetchone()
if result:
    print(f'✅ Test class found in WAMP: {result}')
else:
    print('❌ Test class not found in WAMP')
cur.close()
conn.close()
