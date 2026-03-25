from fastapi import FastAPI
from app.db.init_db import init
from pydantic import BaseModel

from app.db.session import get_connection

app = FastAPI()


class RecognitionItem(BaseModel):
    student_id: str | None
    similarity: float
    confidence: float


class AttendanceIngestRequest(BaseModel):
    matches: list[RecognitionItem]
    source: str = "ai-service"

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