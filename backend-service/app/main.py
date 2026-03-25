from fastapi import FastAPI, Depends, Security
from app.db.init_db import init
from db.session import get_connection
from app.schemas.recognition import RecognitionResult
from app.schemas.session import SessionStart, Session
from app.schemas.student import StudentCreate, Student
from app.schemas.report import AttendanceReport, StudentAttendance
from datetime import datetime
from typing import List
import mysql.connector
from app.core.logging import logger
from app.security import get_api_key

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    init()
    yield

app = FastAPI(lifespan=lifespan)


@app.get("/")
def home():
    return {"message": "Backend running"}

@app.get("/health/db")
def db_health(conn = Depends(get_connection)):
    return {"status": "DB connected"}

@app.post("/register-student", response_model=Student)
async def register_student(student: StudentCreate, conn = Depends(get_connection), api_key: str = Security(get_api_key)):
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "INSERT INTO Student (id, name, email) VALUES (%s, %s, %s)",
            (student.id, student.name, student.email)
        )
        conn.commit()
        cursor.close()
        return student
    except mysql.connector.Error as err:
        logger.error(err)
        conn.rollback()
        cursor.close()
        return {"error": "Database error"}


@app.post("/start-session", response_model=Session)
async def start_session(session_data: SessionStart, conn = Depends(get_connection), api_key: str = Security(get_api_key)):
    cursor = conn.cursor(dictionary=True)
    try:
        start_time = datetime.now()
        cursor.execute(
            "INSERT INTO Session (professor_id, start_time) VALUES (%s, %s)",
            (session_data.professor_id, start_time)
        )
        conn.commit()
        
        session_id = cursor.lastrowid
        
        cursor.close()
        
        return Session(id=session_id, professor_id=session_data.professor_id, start_time=start_time)
    except mysql.connector.Error as err:
        logger.error(err)
        conn.rollback()
        cursor.close()
        return {"error": "Database error"}

@app.post("/stop-session/{session_id}", response_model=Session)
async def stop_session(session_id: int, conn = Depends(get_connection), api_key: str = Security(get_api_key)):
    cursor = conn.cursor(dictionary=True)
    try:
        end_time = datetime.now()
        cursor.execute(
            "UPDATE Session SET end_time = %s WHERE id = %s",
            (end_time, session_id)
        )
        conn.commit()

        cursor.execute("SELECT * FROM Session WHERE id = %s", (session_id,))
        session = cursor.fetchone()

        cursor.close()
        
        return session
    except mysql.connector.Error as err:
        logger.error(err)
        conn.rollback()
        cursor.close()
        return {"error": "Database error"}

@app.post("/recognize-result")
async def recognize_result(recognition_data: RecognitionResult, conn = Depends(get_connection), api_key: str = Security(get_api_key)):
    cursor = conn.cursor(dictionary=True)
    try:
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
        
        return {"message": "Attendance recorded and interval logged successfully."}
    except mysql.connector.Error as err:
        logger.error(err)
        conn.rollback()
        cursor.close()
        return {"error": "Database error"}

@app.get("/attendance-report/{session_id}", response_model=AttendanceReport)
async def get_attendance_report(session_id: int, conn = Depends(get_connection)):
    cursor = conn.cursor(dictionary=True)
    try:
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

        return AttendanceReport(session_id=session_id, report=report)
    except mysql.connector.Error as err:
        logger.error(err)
        cursor.close()
        return {"error": "Database error"}