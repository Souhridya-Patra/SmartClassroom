from fastapi import FastAPI
from app.db.init_db import init
from db.session import get_connection
from app.schemas.recognition import RecognitionResult
from app.schemas.session import SessionStart, Session
from app.schemas.student import StudentCreate, Student
from app.schemas.report import AttendanceReport, StudentAttendance
from datetime import datetime
from typing import List

app = FastAPI()

@app.on_event("startup")
def startup():
    init()

@app.get("/")
def home():
    return {"message": "Backend running"}

@app.get("/health/db")
def db_health():
    conn = get_connection()
    conn.close()
    return {"status": "DB connected"}

@app.post("/register-student", response_model=Student)
async def register_student(student: StudentCreate):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "INSERT INTO Student (id, name, email) VALUES (%s, %s, %s)",
        (student.id, student.name, student.email)
    )
    conn.commit()
    
    cursor.close()
    conn.close()
    
    return student

@app.post("/start-session", response_model=Session)
async def start_session(session_data: SessionStart):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    start_time = datetime.now()
    cursor.execute(
        "INSERT INTO Session (professor_id, start_time) VALUES (%s, %s)",
        (session_data.professor_id, start_time)
    )
    conn.commit()
    
    session_id = cursor.lastrowid
    
    cursor.close()
    conn.close()
    
    return Session(id=session_id, professor_id=session_data.professor_id, start_time=start_time)

@app.post("/recognize-result")
async def recognize_result(recognition_data: RecognitionResult):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    session_id = recognition_data.session_id
    recognized_students = recognition_data.recognized_students
    timestamp = datetime.now()

    # Log to Interval_Log
    recognized_students_str = ",".join(recognized_students)
    cursor.execute(
        "INSERT INTO Interval_Log (session_id, timestamp, recognized_students) VALUES (%s, %s, %s)",
        (session_id, timestamp, recognized_students_str)
    )

    # Insert into Attendance
    for student_id in recognized_students:
        cursor.execute(
            "INSERT INTO Attendance (session_id, student_id, timestamp) VALUES (%s, %s, %s)",
            (session_id, student_id, timestamp)
        )

    conn.commit()
    cursor.close()
    conn.close()
    
    return {"message": "Attendance recorded and interval logged successfully."}

@app.get("/attendance-report/{session_id}", response_model=AttendanceReport)
async def get_attendance_report(session_id: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Get all students
    cursor.execute("SELECT * FROM Student")
    students = cursor.fetchall()

    # Get all attendance records for the session
    cursor.execute("SELECT * FROM Attendance WHERE session_id = %s", (session_id,))
    attendance_records = cursor.fetchall()

    # Create a dictionary to hold attendance data
    attendance_data = {student['id']: [] for student in students}
    for record in attendance_records:
        attendance_data[record['student_id']].append(record['timestamp'])

    # Build the report
    report = []
    for student in students:
        report.append(
            StudentAttendance(
                id=student['id'],
                name=student['name'],
                timestamps=attendance_data[student['id']]
            )
        )

    cursor.close()
    conn.close()

    return AttendanceReport(session_id=session_id, report=report)