from fastapi import FastAPI
from app.db.session import get_connection

app = FastAPI()

# Root check
@app.get("/")
def home():
    return {"message": "Backend is running 🚀"}

# DB health check
@app.get("/health/db")
def check_db():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchall()
        cursor.close()
        conn.close()
        return {"status": "Database connected ✅"}
    except Exception as e:
        return {"error": str(e)}

# Register student
@app.post("/register-student")
def register_student(name: str, department: str, qr_code: str):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        query = """
        INSERT INTO students (name, department, qr_code)
        VALUES (%s, %s, %s)
        """

        cursor.execute(query, (name, department, qr_code))
        conn.commit()

        cursor.close()
        conn.close()

        return {"message": "Student registered successfully ✅"}

    except Exception as e:
        return {"error": str(e)}

# Get all students
@app.get("/students")
def get_students():
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM students")
        data = cursor.fetchall()

        cursor.close()
        conn.close()

        return {"students": data}

    except Exception as e:
        return {"error": str(e)}

# Session starts here
@app.post("/start-session")
def start_session():
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO session (status) VALUES (%s)",
            ("active",)
        )

        conn.commit()

        cursor.close()
        conn.close()

        return {"message": "Session started ✅"}

    except Exception as e:
        return {"error": str(e)}


@app.post("/mark-attendance")
def mark_attendance(session_id: int, student_id: int):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO attendance (session_id, student_id) VALUES (%s, %s)",
            (session_id, student_id)
        )

        conn.commit()

        cursor.close()
        conn.close()

        return {"message": "Attendance marked ✅"}

    except Exception as e:
        return {"error": str(e)}


@app.post("/recognize-result")
def recognize_result(session_id: int, students: list[int]):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        for student_id in students:
            cursor.execute(
                "INSERT INTO attendance (session_id, student_id) VALUES (%s, %s)",
                (session_id, student_id)
            )

        conn.commit()

        cursor.close()
        conn.close()

        return {"message": "Attendance marked from AI ✅"}

    except Exception as e:
        return {"error": str(e)}
    
   
  
  