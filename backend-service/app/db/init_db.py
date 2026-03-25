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

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS attendance_events (
            id INT AUTO_INCREMENT PRIMARY KEY,
            student_id VARCHAR(64) NOT NULL,
            similarity FLOAT NOT NULL,
            confidence FLOAT NOT NULL,
            source VARCHAR(32) NOT NULL DEFAULT 'ai-service',
            event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.commit()
    cursor.close()
    conn.close()

    print("✅ DB Initialized")