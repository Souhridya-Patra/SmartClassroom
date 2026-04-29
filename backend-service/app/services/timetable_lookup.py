import os
from datetime import datetime

import mysql.connector


def _connect_timetable_db():
    return mysql.connector.connect(
        host=os.getenv("TIMETABLE_DB_HOST", os.getenv("DB_HOST", "localhost")),
        port=int(os.getenv("TIMETABLE_DB_PORT", os.getenv("DB_PORT", "3306"))),
        user=os.getenv("TIMETABLE_DB_USER", os.getenv("DB_USER", "root")),
        password=os.getenv("TIMETABLE_DB_PASSWORD", os.getenv("DB_PASSWORD", "")),
        database=os.getenv("TIMETABLE_DB_NAME", os.getenv("DB_NAME", "timetable_db")),
    )


def _derive_section_code(class_row: dict) -> str | None:
    section = (class_row.get("section") or "").strip()
    if section:
        return section

    class_id = (class_row.get("class_id") or "").strip()
    if "-" in class_id:
        suffix = class_id.rsplit("-", 1)[-1].strip()
        if suffix:
            return suffix
    return None


def _find_explicit_mapping(cursor, class_id: str) -> dict | None:
    cursor.execute(
        """
        SELECT
            m.id AS mapping_id,
            m.smart_class_id,
            m.section_id,
            sc.name AS section_name
        FROM smartclassroom_class_section_map m
        JOIN sections sc ON m.section_id = sc.id
        WHERE m.smart_class_id = %s AND m.is_active = 1
        LIMIT 1
        """,
        (class_id,),
    )
    return cursor.fetchone()


def lookup_current_assignment(class_row: dict, when: datetime | None = None) -> dict | None:
    class_id = (class_row.get("class_id") or "").strip()
    section_code = _derive_section_code(class_row)

    moment = when or datetime.now()
    day_of_week = moment.strftime("%A")
    current_time = moment.strftime("%H:%M:%S")

    conn = _connect_timetable_db()
    cursor = conn.cursor(dictionary=True)
    try:
        mapping = _find_explicit_mapping(cursor, class_id) if class_id else None

        params: tuple = ()
        where_clause = ""
        mapping_mode = ""
        if mapping:
            where_clause = "tt.section_id = %s"
            params = (mapping["section_id"], day_of_week, current_time, current_time)
            mapping_mode = "explicit"
        elif section_code:
            where_clause = "sc.name = %s"
            params = (section_code, day_of_week, current_time, current_time)
            mapping_mode = "derived"
        else:
            return None

        cursor.execute(
            f"""
            SELECT
                tt.id AS timetable_id,
                tt.section_id,
                tt.day_of_week,
                tt.slot_id,
                tt.subject_id,
                tt.teacher_id,
                tt.room_id,
                tt.session_type,
                ts.slot_number,
                ts.label AS slot_label,
                ts.start_time,
                ts.end_time,
                sb.name AS subject_name,
                sb.code AS subject_code,
                t.full_name AS teacher_name,
                r.name AS room_name,
                r.room_type,
                sc.name AS section_name,
                sm.sem_number,
                d.name AS dept_name
            FROM timetable tt
            JOIN time_slots ts ON tt.slot_id = ts.id
            JOIN subjects sb ON tt.subject_id = sb.id
            JOIN teachers t ON tt.teacher_id = t.id
            JOIN rooms r ON tt.room_id = r.id
            JOIN sections sc ON tt.section_id = sc.id
            JOIN semesters sm ON sc.sem_id = sm.id
            JOIN departments d ON sm.dept_id = d.id
            WHERE {where_clause}
              AND tt.day_of_week = %s
              AND %s >= ts.start_time
              AND %s <= ts.end_time
            ORDER BY ts.slot_number
            LIMIT 1
            """,
            params,
        )
        row = cursor.fetchone()
        if not row:
            return None
        row["mapping_mode"] = mapping_mode
        row["mapped_by_class_id"] = class_id if mapping else None
        row["mapping_id"] = mapping["mapping_id"] if mapping else None
        row["matched_section_code"] = section_code
        row["matched_day_of_week"] = day_of_week
        row["matched_time"] = current_time
        return row
    finally:
        cursor.close()
        conn.close()


def get_timetable_health() -> dict:
    conn = _connect_timetable_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT 1")
        cursor.fetchone()
        return {
            "status": "connected",
            "database": os.getenv("TIMETABLE_DB_NAME", os.getenv("DB_NAME", "timetable_db")),
        }
    finally:
        cursor.close()
        conn.close()


def list_timetable_rooms() -> list[str]:
    conn = _connect_timetable_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT name FROM rooms ORDER BY name")
        rows = cursor.fetchall()
        return [row["name"] for row in rows]
    finally:
        cursor.close()
        conn.close()


def lookup_current_assignment_by_room(room_name: str, when: datetime | None = None) -> dict | None:
    room_name = (room_name or "").strip()
    if not room_name:
        return None

    moment = when or datetime.now()
    day_of_week = moment.strftime("%A")
    current_time = moment.strftime("%H:%M:%S")

    conn = _connect_timetable_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT
                tt.id AS timetable_id,
                tt.section_id,
                tt.day_of_week,
                tt.slot_id,
                tt.subject_id,
                tt.teacher_id,
                tt.room_id,
                tt.session_type,
                ts.slot_number,
                ts.label AS slot_label,
                ts.start_time,
                ts.end_time,
                sb.name AS subject_name,
                sb.code AS subject_code,
                t.full_name AS teacher_name,
                r.name AS room_name,
                r.room_type,
                sc.name AS section_name,
                sm.sem_number,
                d.name AS dept_name,
                m.smart_class_id,
                m.id AS mapping_id
            FROM timetable tt
            JOIN time_slots ts ON tt.slot_id = ts.id
            JOIN subjects sb ON tt.subject_id = sb.id
            JOIN teachers t ON tt.teacher_id = t.id
            JOIN rooms r ON tt.room_id = r.id
            JOIN sections sc ON tt.section_id = sc.id
            JOIN semesters sm ON sc.sem_id = sm.id
            JOIN departments d ON sm.dept_id = d.id
            LEFT JOIN smartclassroom_class_section_map m
                ON m.section_id = tt.section_id
               AND m.is_active = 1
            WHERE r.name = %s
              AND tt.day_of_week = %s
              AND %s >= ts.start_time
              AND %s <= ts.end_time
            ORDER BY ts.slot_number
            LIMIT 1
            """,
            (room_name, day_of_week, current_time, current_time),
        )
        row = cursor.fetchone()
        if not row:
            return None
        row["matched_day_of_week"] = day_of_week
        row["matched_time"] = current_time
        return row
    finally:
        cursor.close()
        conn.close()


def lookup_nearest_assignment_by_room(room_name: str, when: datetime | None = None) -> dict | None:
    room_name = (room_name or "").strip()
    if not room_name:
        return None

    moment = when or datetime.now()
    day_of_week = moment.strftime("%A")
    current_time = moment.strftime("%H:%M:%S")

    conn = _connect_timetable_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT
                tt.id AS timetable_id,
                tt.section_id,
                tt.day_of_week,
                tt.slot_id,
                tt.subject_id,
                tt.teacher_id,
                tt.room_id,
                tt.session_type,
                ts.slot_number,
                ts.label AS slot_label,
                ts.start_time,
                ts.end_time,
                sb.name AS subject_name,
                sb.code AS subject_code,
                t.full_name AS teacher_name,
                r.name AS room_name,
                r.room_type,
                sc.name AS section_name,
                sm.sem_number,
                d.name AS dept_name,
                m.smart_class_id,
                m.id AS mapping_id
            FROM timetable tt
            JOIN time_slots ts ON tt.slot_id = ts.id
            JOIN subjects sb ON tt.subject_id = sb.id
            JOIN teachers t ON tt.teacher_id = t.id
            JOIN rooms r ON tt.room_id = r.id
            JOIN sections sc ON tt.section_id = sc.id
            JOIN semesters sm ON sc.sem_id = sm.id
            JOIN departments d ON sm.dept_id = d.id
            LEFT JOIN smartclassroom_class_section_map m
                ON m.section_id = tt.section_id
               AND m.is_active = 1
            WHERE r.name = %s
              AND tt.day_of_week = %s
            ORDER BY
                CASE WHEN ts.start_time >= %s THEN 0 ELSE 1 END,
                ABS(TIME_TO_SEC(TIMEDIFF(ts.start_time, %s)))
            LIMIT 1
            """,
            (room_name, day_of_week, current_time, current_time),
        )
        row = cursor.fetchone()
        if not row:
            return None
        row["matched_day_of_week"] = day_of_week
        row["matched_time"] = current_time
        return row
    finally:
        cursor.close()
        conn.close()