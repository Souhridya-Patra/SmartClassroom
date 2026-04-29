import os
import re

import mysql.connector

from db.connection import get_connection


def _connect_admin():
    host = os.getenv("TIMETABLE_DB_HOST", os.getenv("DB_HOST", "localhost"))
    port = int(os.getenv("TIMETABLE_DB_PORT", os.getenv("DB_PORT", "3306")))
    user = os.getenv("TIMETABLE_DB_USER", os.getenv("DB_USER", "root"))
    password = os.getenv("TIMETABLE_DB_PASSWORD", os.getenv("DB_PASSWORD", ""))
    database = os.getenv("TIMETABLE_DB_NAME", os.getenv("DB_NAME", "timetable_db"))

    conn = mysql.connector.connect(
        host=host,
        port=port,
        user=user,
        password=password,
    )
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database}")
    conn.commit()
    cursor.close()
    conn.close()


def _split_sql_statements(sql_text: str) -> list[str]:
    cleaned_lines: list[str] = []
    for line in sql_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        if "--" in line:
            line = line.split("--", 1)[0]
        cleaned_lines.append(line)

    cleaned_sql = "\n".join(cleaned_lines)
    statements = [statement.strip() for statement in re.split(r";\s*", cleaned_sql) if statement.strip()]
    return statements


def init_database() -> None:
    _connect_admin()

    conn = get_connection()
    cursor = conn.cursor()

    with open(os.path.join(os.path.dirname(__file__), "schema.sql"), "r", encoding="utf-8") as handle:
        sql_text = handle.read()

    for statement in _split_sql_statements(sql_text):
        upper = statement.upper()
        if upper.startswith("CREATE DATABASE") or upper.startswith("USE "):
            continue
        try:
            cursor.execute(statement)
        except mysql.connector.Error as exc:
            message = str(exc).lower()
            if "already exists" not in message and "duplicate" not in message:
                raise

    # Backward-compatible migrations for older timetable_db schemas.
    migration_sql = [
        # semesters
        "ALTER TABLE semesters ADD COLUMN teaching_weeks INT NOT NULL DEFAULT 16",

        # subjects: support newer scheduler model while preserving old data
        "ALTER TABLE subjects MODIFY COLUMN subject_type ENUM('theory','practical','theory+practical','lab') NOT NULL DEFAULT 'theory'",
        "ALTER TABLE subjects ADD COLUMN theory_hours INT NULL",
        "ALTER TABLE subjects ADD COLUMN practical_hours INT NULL",
        "ALTER TABLE subjects ADD COLUMN lab_slots_per_session INT NOT NULL DEFAULT 2",

        # section-subject-teacher mapping newer shape (scheduler already has fallback,
        # but these help match standalone project behavior)
        "ALTER TABLE section_subject_teacher ADD COLUMN theory_teacher_id INT NULL",
        "ALTER TABLE section_subject_teacher ADD COLUMN practical_teacher_id INT NULL",
    ]

    for statement in migration_sql:
        try:
            cursor.execute(statement)
        except mysql.connector.Error as exc:
            message = str(exc).lower()
            if "duplicate column" in message or "already exists" in message:
                continue
            if "cannot be null" in message:
                continue
            if "data truncated" in message:
                continue
            raise

    # Data backfill for legacy rows.
    backfill_sql = [
        "UPDATE semesters SET teaching_weeks = 16 WHERE teaching_weeks IS NULL OR teaching_weeks <= 0",
        "UPDATE subjects SET theory_hours = COALESCE(theory_hours, hours_per_week * 16)",
        "UPDATE subjects SET practical_hours = COALESCE(practical_hours, CASE WHEN subject_type IN ('practical','lab') THEN hours_per_week * 16 ELSE 0 END)",
        "UPDATE subjects SET lab_slots_per_session = COALESCE(NULLIF(lab_slots_per_session, 0), lab_slots, 2)",
        "UPDATE subjects SET subject_type = 'practical' WHERE subject_type = 'lab'",
        "UPDATE section_subject_teacher SET theory_teacher_id = COALESCE(theory_teacher_id, teacher_id)",
        "UPDATE section_subject_teacher SET practical_teacher_id = COALESCE(practical_teacher_id, teacher_id)",
    ]

    for statement in backfill_sql:
        try:
            cursor.execute(statement)
        except mysql.connector.Error:
            # Keep init resilient across schema variants.
            pass

    conn.commit()
    cursor.close()
    conn.close()