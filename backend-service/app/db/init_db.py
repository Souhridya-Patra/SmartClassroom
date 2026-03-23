from app.db.session import get_connection

def init():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS test_table (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(50)
    )
    """)

    conn.commit()
    cursor.close()
    conn.close()

    print("✅ DB Initialized")