import os
from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from app.db.init_db import init
from pydantic import BaseModel, Field
import requests

from app.db.session import get_connection

app = FastAPI()


class RecognitionItem(BaseModel):
    student_id: str | None
    similarity: float
    confidence: float


class AttendanceIngestRequest(BaseModel):
    matches: list[RecognitionItem]
    source: str = "ai-service"


class StudentInfo(BaseModel):
    student_id: str
    enrollment_date: str | None
    updated_at: str | None


class EmbeddingInfo(BaseModel):
    student_id: str
    samples_count: int
    created_at: str | None


class FacultyRegisterRequest(BaseModel):
    faculty_id: str
    full_name: str
    barcode_value: str
    face_identity_id: str


class FacultyVerificationRequest(BaseModel):
    faculty_id: str
    barcode_value: str
    recognized_face_id: str


class FacultyCheckInRequest(BaseModel):
    """Faculty image + barcode check-in for orchestrated verification."""
    faculty_id: str
    barcode_value: str


class ClassCreateRequest(BaseModel):
    class_id: str
    class_name: str
    section: str | None = None
    semester: str | None = None


class ClassStudentEnrollRequest(BaseModel):
    student_ids: list[str] = Field(default_factory=list)


class SessionStartRequest(BaseModel):
    class_id: str
    faculty_id: str
    barcode_value: str
    recognized_face_id: str


class SessionEndRequest(BaseModel):
    faculty_id: str
    barcode_value: str
    recognized_face_id: str


def _verify_faculty(
    cursor,
    faculty_id: str,
    barcode_value: str,
    recognized_face_id: str,
) -> tuple[bool, bool, dict]:
    cursor.execute(
        """
        SELECT faculty_id, full_name, barcode_value, face_identity_id
        FROM faculty
        WHERE faculty_id = %s
        """,
        (faculty_id,),
    )
    faculty = cursor.fetchone()
    if not faculty:
        raise HTTPException(status_code=404, detail=f"Faculty {faculty_id} not found")

    barcode_ok = faculty["barcode_value"] == barcode_value
    face_ok = faculty["face_identity_id"] == recognized_face_id
    return barcode_ok, face_ok, faculty

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


@app.post("/attendance/recognition")
def ingest_attendance(payload: AttendanceIngestRequest):
    conn = get_connection()
    cursor = conn.cursor()

    rows_inserted = 0
    for item in payload.matches:
        if not item.student_id:
            continue
        cursor.execute(
            """
            INSERT INTO attendance_events (student_id, similarity, confidence, source)
            VALUES (%s, %s, %s, %s)
            """,
            (item.student_id, item.similarity, item.confidence, payload.source),
        )
        rows_inserted += 1

    conn.commit()
    cursor.close()
    conn.close()

    return {"inserted": rows_inserted}


@app.get("/attendance/recent")
def attendance_recent(limit: int = 20):
    safe_limit = max(1, min(limit, 200))
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT student_id, similarity, confidence, source, event_time
        FROM attendance_events
        ORDER BY id DESC
        LIMIT %s
        """,
        (safe_limit,),
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return {"events": rows}


@app.get("/attendance/summary")
def attendance_summary():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM attendance_events")
    total_events = int(cursor.fetchone()[0])
    cursor.execute("SELECT COUNT(DISTINCT student_id) FROM attendance_events")
    unique_students = int(cursor.fetchone()[0])
    cursor.close()
    conn.close()
    return {
        "total_events": total_events,
        "unique_students": unique_students,
    }


@app.get("/students", response_model=list[StudentInfo])
def list_students():
    """List all enrolled students."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT id, enrollment_date, updated_at
        FROM students
        ORDER BY enrollment_date DESC
        """
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    result = []
    for row in rows:
        result.append(
            StudentInfo(
                student_id=row["id"],
                enrollment_date=str(row["enrollment_date"]) if row["enrollment_date"] else None,
                updated_at=str(row["updated_at"]) if row["updated_at"] else None,
            )
        )
    return result


@app.get("/students/{student_id}")
def get_student(student_id: str):
    """Get detailed info for a student."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute(
        "SELECT id, enrollment_date, updated_at FROM students WHERE id = %s",
        (student_id,),
    )
    row = cursor.fetchone()
    if not row:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail=f"Student {student_id} not found")
    
    cursor.execute(
        """
        SELECT COUNT(*) as total_events, 
               AVG(similarity) as avg_similarity,
               MAX(similarity) as best_match
        FROM attendance_events WHERE student_id = %s
        """,
        (student_id,),
    )
    stats = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    return {
        "student_id": row["id"],
        "enrollment_date": str(row["enrollment_date"]) if row["enrollment_date"] else None,
        "updated_at": str(row["updated_at"]) if row["updated_at"] else None,
        "attendance_count": int(stats["total_events"]) if stats and stats["total_events"] else 0,
        "avg_similarity": round(float(stats["avg_similarity"]), 4) if stats and stats["avg_similarity"] else 0.0,
        "best_match": round(float(stats["best_match"]), 4) if stats and stats["best_match"] else 0.0,
    }


@app.get("/students/{student_id}/embeddings", response_model=list[EmbeddingInfo])
def get_student_embeddings(student_id: str):
    """Get all embedding records for a student."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute(
        """
        SELECT student_id, samples_count, created_at
        FROM facial_embeddings
        WHERE student_id = %s
        ORDER BY created_at DESC
        """,
        (student_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if not rows:
        raise HTTPException(status_code=404, detail=f"No embeddings found for {student_id}")
    
    result = []
    for row in rows:
        result.append(
            EmbeddingInfo(
                student_id=row["student_id"],
                samples_count=int(row["samples_count"]),
                created_at=str(row["created_at"]) if row["created_at"] else None,
            )
        )
    return result


@app.delete("/students/{student_id}")
def delete_student(student_id: str):
    """Delete a student and all their embeddings and attendance records."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if student exists
    cursor.execute("SELECT id FROM students WHERE id = %s", (student_id,))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail=f"Student {student_id} not found")
    
    # Delete student (cascades to embeddings and attendance events)
    cursor.execute("DELETE FROM students WHERE id = %s", (student_id,))
    rows_affected = cursor.rowcount
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return {"deleted": rows_affected, "student_id": student_id}


@app.post("/faculty/register")
def register_faculty(payload: FacultyRegisterRequest):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO faculty (faculty_id, full_name, barcode_value, face_identity_id)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            full_name = VALUES(full_name),
            barcode_value = VALUES(barcode_value),
            face_identity_id = VALUES(face_identity_id)
        """,
        (
            payload.faculty_id.strip(),
            payload.full_name.strip(),
            payload.barcode_value.strip(),
            payload.face_identity_id.strip(),
        ),
    )

    conn.commit()
    cursor.close()
    conn.close()
    return {
        "faculty_id": payload.faculty_id.strip(),
        "message": "Faculty profile saved",
        "note": "Enroll faculty face in AI service using face_identity_id for face verification.",
    }


@app.post("/faculty/verify")
def verify_faculty(payload: FacultyVerificationRequest):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    barcode_ok, face_ok, faculty = _verify_faculty(
        cursor,
        payload.faculty_id.strip(),
        payload.barcode_value.strip(),
        payload.recognized_face_id.strip(),
    )
    cursor.close()
    conn.close()

    return {
        "verified": barcode_ok and face_ok,
        "barcode_verified": barcode_ok,
        "face_verified": face_ok,
        "faculty_id": faculty["faculty_id"],
        "full_name": faculty["full_name"],
    }


@app.post("/faculty/checkin-with-image")
async def faculty_checkin_with_image(
    faculty_id: str = Form(...),
    barcode_value: str = Form(...),
    image: UploadFile = File(...),
):
    """
    Orchestrated endpoint: Accept faculty_id, barcode, and image.
    Perform AI face recognition + backend barcode + face verification in one call.
    """
    ai_service_url = os.getenv("AI_SERVICE_URL", "http://ai-service:8000")
    
    # Step 1: Call AI service to recognize face in image
    try:
        image_data = await image.read()
        files = {"image": ("image.jpg", image_data, "image/jpeg")}
        recognition_response = requests.post(
            f"{ai_service_url}/recognize",
            files=files,
            params={"identity_prefix": "FACE-"},
            timeout=30,
        )
        recognition_response.raise_for_status()
        recognition_result = recognition_response.json()
    except requests.RequestException as e:
        raise HTTPException(
            status_code=503,
            detail=f"AI service error: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Image processing error: {str(e)}",
        )

    # Step 2: Extract best face match from recognition
    matches = recognition_result.get("matches", [])
    if not matches:
        raise HTTPException(
            status_code=422,
            detail="No face detected in image",
        )

    best_match = max(matches, key=lambda m: m.get("similarity", 0))
    recognized_face_id = best_match.get("student_id")
    if not recognized_face_id:
        raise HTTPException(
            status_code=422,
            detail="Face recognized but no student ID matched",
        )

    # Step 3: Verify faculty with barcode + recognized face
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        barcode_ok, face_ok, faculty = _verify_faculty(
            cursor,
            faculty_id.strip(),
            barcode_value.strip(),
            recognized_face_id.strip(),
        )
    except HTTPException:
        cursor.close()
        conn.close()
        raise
    finally:
        cursor.close()
        conn.close()

    return {
        "verified": barcode_ok and face_ok,
        "barcode_verified": barcode_ok,
        "face_verified": face_ok,
        "faculty_id": faculty["faculty_id"],
        "full_name": faculty["full_name"],
        "recognition_details": {
            "similarity": best_match.get("similarity"),
            "confidence": best_match.get("confidence"),
        },
    }


@app.post("/classes")
def create_class(payload: ClassCreateRequest):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO classes (class_id, class_name, section, semester)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            class_name = VALUES(class_name),
            section = VALUES(section),
            semester = VALUES(semester)
        """,
        (
            payload.class_id.strip(),
            payload.class_name.strip(),
            payload.section.strip() if payload.section else None,
            payload.semester.strip() if payload.semester else None,
        ),
    )
    conn.commit()
    cursor.close()
    conn.close()
    return {"class_id": payload.class_id.strip(), "message": "Class saved"}


@app.post("/classes/{class_id}/students/enroll")
def enroll_students_in_class(class_id: str, payload: ClassStudentEnrollRequest):
    if not payload.student_ids:
        raise HTTPException(status_code=400, detail="student_ids is required")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT class_id FROM classes WHERE class_id = %s", (class_id,))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail=f"Class {class_id} not found")

    inserted = 0
    for student_id in payload.student_ids:
        sid = student_id.strip()
        if not sid:
            continue

        cursor.execute("SELECT id FROM students WHERE id = %s", (sid,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO students (id) VALUES (%s)", (sid,))

        cursor.execute(
            """
            INSERT INTO student_class_enrollments (student_id, class_id, active)
            VALUES (%s, %s, 1)
            ON DUPLICATE KEY UPDATE active = 1
            """,
            (sid, class_id),
        )
        inserted += 1

    conn.commit()
    cursor.close()
    conn.close()

    return {
        "class_id": class_id,
        "enrolled_count": inserted,
        "message": "Students enrolled/updated for class",
    }


@app.get("/classes/{class_id}/students")
def list_class_students(class_id: str):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT sce.student_id, s.enrollment_date
        FROM student_class_enrollments sce
        JOIN students s ON s.id = sce.student_id
        WHERE sce.class_id = %s AND sce.active = 1
        ORDER BY sce.student_id ASC
        """,
        (class_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return {"class_id": class_id, "students": rows, "count": len(rows)}


@app.post("/sessions/start")
def start_session(payload: SessionStartRequest):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT class_id FROM classes WHERE class_id = %s", (payload.class_id.strip(),))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail=f"Class {payload.class_id} not found")

    barcode_ok, face_ok, _ = _verify_faculty(
        cursor,
        payload.faculty_id.strip(),
        payload.barcode_value.strip(),
        payload.recognized_face_id.strip(),
    )
    if not (barcode_ok and face_ok):
        cursor.close()
        conn.close()
        raise HTTPException(
            status_code=401,
            detail={
                "message": "Faculty verification failed",
                "barcode_verified": barcode_ok,
                "face_verified": face_ok,
            },
        )

    cursor.execute(
        """
        SELECT session_id
        FROM class_sessions
        WHERE class_id = %s AND status = 'active'
        ORDER BY session_id DESC
        LIMIT 1
        """,
        (payload.class_id.strip(),),
    )
    active = cursor.fetchone()
    if active:
        cursor.close()
        conn.close()
        raise HTTPException(
            status_code=409,
            detail=f"Class {payload.class_id} already has active session {active['session_id']}",
        )

    # AUTO-MAPPING: Find matching timetable period for current day/time
    from datetime import datetime
    current_time = datetime.now().strftime("%H:%M:%S")
    current_day = datetime.now().strftime("%A")  # e.g., "Monday"

    period_id = None
    timetable_schedule_id = None
    matched_subject = None

    cursor.execute(
        """
        SELECT t.schedule_id, sp.period_id, sp.subject_name
        FROM timetable t
        LEFT JOIN subject_periods sp ON t.schedule_id = sp.timetable_id
        WHERE t.class_id = %s
          AND t.day_of_week = %s
          AND %s >= t.start_time AND %s <= t.end_time
        LIMIT 1
        """,
        (payload.class_id.strip(), current_day, current_time, current_time),
    )
    timetable_match = cursor.fetchone()
    if timetable_match:
        timetable_schedule_id = timetable_match["schedule_id"]
        period_id = timetable_match["period_id"]
        matched_subject = timetable_match["subject_name"]

    cursor.execute(
        """
        INSERT INTO class_sessions (
            class_id,
            faculty_id,
            period_id,
            timetable_schedule_id,
            status,
            start_barcode_verified,
            start_face_verified
        ) VALUES (%s, %s, %s, %s, 'active', 1, 1)
        """,
        (payload.class_id.strip(), payload.faculty_id.strip(), period_id, timetable_schedule_id),
    )
    session_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()

    response = {
        "session_id": session_id,
        "class_id": payload.class_id.strip(),
        "faculty_id": payload.faculty_id.strip(),
        "status": "active",
        "message": "Session started after barcode + face verification",
        "auto_mapped_period": {
            "period_id": period_id,
            "subject_name": matched_subject,
            "timetable_schedule_id": timetable_schedule_id,
        } if period_id else None,
    }
    if matched_subject:
        response["message"] += f" (Period: {matched_subject})"

    return response


@app.post("/sessions/{session_id}/end")
def end_session(session_id: int, payload: SessionEndRequest):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT session_id, class_id, faculty_id, start_time, status
        FROM class_sessions
        WHERE session_id = %s
        """,
        (session_id,),
    )
    session = cursor.fetchone()
    if not session:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    if session["status"] != "active":
        cursor.close()
        conn.close()
        raise HTTPException(status_code=409, detail=f"Session {session_id} is already closed")
    if session["faculty_id"] != payload.faculty_id.strip():
        cursor.close()
        conn.close()
        raise HTTPException(status_code=403, detail="Session can only be ended by the same faculty")

    barcode_ok, face_ok, _ = _verify_faculty(
        cursor,
        payload.faculty_id.strip(),
        payload.barcode_value.strip(),
        payload.recognized_face_id.strip(),
    )
    if not (barcode_ok and face_ok):
        cursor.close()
        conn.close()
        raise HTTPException(
            status_code=401,
            detail={
                "message": "Faculty verification failed",
                "barcode_verified": barcode_ok,
                "face_verified": face_ok,
            },
        )

    cursor.execute(
        """
        UPDATE class_sessions
        SET
            end_time = CURRENT_TIMESTAMP,
            status = 'completed',
            end_barcode_verified = 1,
            end_face_verified = 1
        WHERE session_id = %s
        """,
        (session_id,),
    )

    cursor.execute(
        """
        SELECT start_time, end_time, class_id
        FROM class_sessions
        WHERE session_id = %s
        """,
        (session_id,),
    )
    finalized_session = cursor.fetchone()

    cursor.execute(
        """
        SELECT student_id
        FROM student_class_enrollments
        WHERE class_id = %s AND active = 1
        """,
        (finalized_session["class_id"],),
    )
    enrolled_rows = cursor.fetchall()
    enrolled_students = {row["student_id"] for row in enrolled_rows}

    present_students: set[str] = set()
    if enrolled_students:
        placeholders = ",".join(["%s"] * len(enrolled_students))
        params = [
            finalized_session["start_time"],
            finalized_session["end_time"],
            *list(enrolled_students),
        ]
        cursor.execute(
            f"""
            SELECT DISTINCT student_id
            FROM attendance_events
            WHERE
                event_time BETWEEN %s AND %s
                AND student_id IN ({placeholders})
            """,
            tuple(params),
        )
        present_rows = cursor.fetchall()
        present_students = {row["student_id"] for row in present_rows}

    absent_students = enrolled_students - present_students

    for student_id in present_students:
        cursor.execute(
            """
            INSERT INTO session_attendance (session_id, class_id, student_id, status)
            VALUES (%s, %s, %s, 'present')
            ON DUPLICATE KEY UPDATE
                status = VALUES(status),
                marked_at = CURRENT_TIMESTAMP
            """,
            (session_id, finalized_session["class_id"], student_id),
        )

    for student_id in absent_students:
        cursor.execute(
            """
            INSERT INTO session_attendance (session_id, class_id, student_id, status)
            VALUES (%s, %s, %s, 'absent')
            ON DUPLICATE KEY UPDATE
                status = VALUES(status),
                marked_at = CURRENT_TIMESTAMP
            """,
            (session_id, finalized_session["class_id"], student_id),
        )

    conn.commit()
    cursor.close()
    conn.close()

    return {
        "session_id": session_id,
        "class_id": finalized_session["class_id"],
        "status": "completed",
        "present_count": len(present_students),
        "absent_count": len(absent_students),
        "present_students": sorted(list(present_students)),
        "absent_students": sorted(list(absent_students)),
    }


@app.get("/sessions/{session_id}/attendance")
def session_attendance(session_id: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT session_id, class_id, faculty_id, start_time, end_time, status
        FROM class_sessions
        WHERE session_id = %s
        """,
        (session_id,),
    )
    session = cursor.fetchone()
    if not session:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    cursor.execute(
        """
        SELECT student_id, status, marked_at
        FROM session_attendance
        WHERE session_id = %s
        ORDER BY student_id
        """,
        (session_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    present_count = len([row for row in rows if row["status"] == "present"])
    absent_count = len([row for row in rows if row["status"] == "absent"])

    return {
        "session": session,
        "present_count": present_count,
        "absent_count": absent_count,
        "attendance": rows,
    }