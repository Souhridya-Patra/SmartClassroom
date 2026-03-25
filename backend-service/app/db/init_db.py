from app.db.session import get_connection

def init():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Professor (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        email VARCHAR(255) UNIQUE NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Student (
        id VARCHAR(255) PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        email VARCHAR(255) UNIQUE NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Session (
        id INT AUTO_INCREMENT PRIMARY KEY,
        professor_id INT,
        start_time DATETIME NOT NULL,
        end_time DATETIME,
        FOREIGN KEY (professor_id) REFERENCES Professor(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Attendance (
        id INT AUTO_INCREMENT PRIMARY KEY,
        session_id INT,
        student_id VARCHAR(255),
        timestamp DATETIME NOT NULL,
        FOREIGN KEY (session_id) REFERENCES Session(id),
        FOREIGN KEY (student_id) REFERENCES Student(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Interval_Log (
        id INT AUTO_INCREMENT PRIMARY KEY,
        session_id INT,
        timestamp DATETIME NOT NULL,
        recognized_students TEXT,
        FOREIGN KEY (session_id) REFERENCES Session(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Device (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        location VARCHAR(255)
    )
    """)

    conn.commit()
    cursor.close()
    conn.close()

    print("✅ DB Initialized")