from __future__ import annotations

import sys
from pathlib import Path

# Ensure top-level packages (e.g., db/) are importable when executed as a script.
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from db.connection import execute_query


def table_columns(table_name: str) -> set[str]:
    rows = execute_query(f"SHOW COLUMNS FROM {table_name}", fetch=True)
    return {row["Field"] for row in rows}


def has_rows(table_name: str) -> bool:
    row = execute_query(f"SELECT COUNT(*) AS c FROM {table_name}", fetch=True)[0]
    return int(row["c"]) > 0


def seed_departments() -> dict[str, int]:
    data = [
        ("Computer Science and Engineering", "CSE"),
        ("Electronics and Communication", "ECE"),
        ("Mechanical Engineering", "ME"),
    ]
    for name, code in data:
        execute_query(
            """
            INSERT INTO departments (name, code)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE name = VALUES(name)
            """,
            (name, code),
        )

    rows = execute_query("SELECT id, code FROM departments", fetch=True)
    return {r["code"]: int(r["id"]) for r in rows}


def seed_semesters(dept_ids: dict[str, int]) -> dict[tuple[str, int], int]:
    cols = table_columns("semesters")
    has_weeks = "teaching_weeks" in cols

    entries = [
        (dept_ids["CSE"], "Semester 3", 3, 16),
        (dept_ids["CSE"], "Semester 5", 5, 16),
        (dept_ids["ECE"], "Semester 3", 3, 16),
        (dept_ids["ME"], "Semester 3", 3, 16),
    ]

    for dept_id, name, sem_number, teaching_weeks in entries:
        if has_weeks:
            execute_query(
                """
                INSERT INTO semesters (dept_id, name, sem_number, teaching_weeks)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE name = VALUES(name), teaching_weeks = VALUES(teaching_weeks)
                """,
                (dept_id, name, sem_number, teaching_weeks),
            )
        else:
            execute_query(
                """
                INSERT INTO semesters (dept_id, name, sem_number)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE name = VALUES(name)
                """,
                (dept_id, name, sem_number),
            )

    rows = execute_query(
        """
        SELECT s.id, d.code AS dept_code, s.sem_number
        FROM semesters s
        JOIN departments d ON d.id = s.dept_id
        """,
        fetch=True,
    )
    return {(r["dept_code"], int(r["sem_number"])): int(r["id"]) for r in rows}


def seed_sections(semester_ids: dict[tuple[str, int], int]) -> dict[tuple[int, str], int]:
    entries = [
        (semester_ids[("CSE", 3)], "A", 68),
        (semester_ids[("CSE", 3)], "B", 62),
        (semester_ids[("CSE", 5)], "A", 58),
        (semester_ids[("ECE", 3)], "A", 60),
        (semester_ids[("ME", 3)], "A", 54),
    ]

    for sem_id, section_name, strength in entries:
        execute_query(
            """
            INSERT INTO sections (sem_id, name, strength)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE strength = VALUES(strength)
            """,
            (sem_id, section_name, strength),
        )

    rows = execute_query("SELECT id, sem_id, name FROM sections", fetch=True)
    return {(int(r["sem_id"]), r["name"]): int(r["id"]) for r in rows}


def seed_rooms(dept_ids: dict[str, int]) -> dict[str, int]:
    entries = [
        ("CSE-101", "classroom", 80, dept_ids["CSE"]),
        ("CSE-102", "classroom", 80, dept_ids["CSE"]),
        ("ECE-201", "classroom", 75, dept_ids["ECE"]),
        ("ME-301", "classroom", 70, dept_ids["ME"]),
        ("LAB-CSE-A", "lab", 40, dept_ids["CSE"]),
        ("LAB-CSE-B", "lab", 35, dept_ids["CSE"]),
        ("LAB-ECE-A", "lab", 36, dept_ids["ECE"]),
    ]

    for name, room_type, capacity, dept_id in entries:
        execute_query(
            """
            INSERT INTO rooms (name, room_type, capacity, dept_id)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE room_type = VALUES(room_type), capacity = VALUES(capacity), dept_id = VALUES(dept_id)
            """,
            (name, room_type, capacity, dept_id),
        )

    rows = execute_query("SELECT id, name FROM rooms", fetch=True)
    return {r["name"]: int(r["id"]) for r in rows}


def seed_teachers(dept_ids: dict[str, int]) -> dict[str, int]:
    entries = [
        ("Dr. Aarav Sharma", "aarav.sharma@inst.edu", dept_ids["CSE"], 18),
        ("Dr. Nisha Verma", "nisha.verma@inst.edu", dept_ids["CSE"], 20),
        ("Prof. Kiran Rao", "kiran.rao@inst.edu", dept_ids["CSE"], 16),
        ("Dr. Meera Nair", "meera.nair@inst.edu", dept_ids["ECE"], 18),
        ("Prof. Rohan Das", "rohan.das@inst.edu", dept_ids["ME"], 18),
    ]

    for full_name, email, dept_id, max_hours_week in entries:
        execute_query(
            """
            INSERT INTO teachers (full_name, email, dept_id, max_hours_week)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE dept_id = VALUES(dept_id), max_hours_week = VALUES(max_hours_week)
            """,
            (full_name, email, dept_id, max_hours_week),
        )

    rows = execute_query("SELECT id, full_name FROM teachers", fetch=True)
    teacher_ids = {r["full_name"]: int(r["id"]) for r in rows}

    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    for tid in teacher_ids.values():
        for day in weekdays:
            execute_query(
                """
                INSERT INTO teacher_availability (teacher_id, day_of_week, is_available)
                VALUES (%s, %s, 1)
                ON DUPLICATE KEY UPDATE is_available = VALUES(is_available)
                """,
                (tid, day),
            )

    return teacher_ids


def seed_timeslots() -> dict[int, int]:
    if has_rows("time_slots"):
        rows = execute_query("SELECT id, slot_number FROM time_slots", fetch=True)
        return {int(r["slot_number"]): int(r["id"]) for r in rows}

    entries = [
        (1, "Period 1", "09:00", "10:00", 0),
        (2, "Period 2", "10:00", "11:00", 0),
        (3, "Period 3", "11:00", "12:00", 0),
        (4, "Lunch Break", "12:00", "13:00", 1),
        (5, "Period 4", "13:00", "14:00", 0),
        (6, "Period 5", "14:00", "15:00", 0),
        (7, "Period 6", "15:00", "16:00", 0),
    ]
    for slot_number, label, start_time, end_time, is_break in entries:
        execute_query(
            """
            INSERT INTO time_slots (slot_number, label, start_time, end_time, is_break)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE label = VALUES(label), start_time = VALUES(start_time), end_time = VALUES(end_time), is_break = VALUES(is_break)
            """,
            (slot_number, label, start_time, end_time, is_break),
        )

    rows = execute_query("SELECT id, slot_number FROM time_slots", fetch=True)
    return {int(r["slot_number"]): int(r["id"]) for r in rows}


def seed_subjects(semester_ids: dict[tuple[str, int], int]) -> dict[tuple[int, str], int]:
    cols = table_columns("subjects")
    uses_theory_practical = {"theory_hours", "practical_hours", "lab_slots_per_session"}.issubset(cols)

    entries = [
        (semester_ids[("CSE", 3)], "Data Structures", "CSE301", "theory", 48, None, None),
        (semester_ids[("CSE", 3)], "DBMS", "CSE302", "theory", 48, None, None),
        (semester_ids[("CSE", 3)], "DBMS Lab", "CSE3L1", "practical", None, 32, 2),
        (semester_ids[("CSE", 3)], "Operating Systems", "CSE303", "theory+practical", 40, 24, 2),
        (semester_ids[("CSE", 5)], "Computer Networks", "CSE501", "theory", 48, None, None),
        (semester_ids[("ECE", 3)], "Signals & Systems", "ECE301", "theory", 48, None, None),
        (semester_ids[("ME", 3)], "Thermodynamics", "ME301", "theory", 48, None, None),
    ]

    for sem_id, name, code, subject_type, th, pr, lab_slots in entries:
        if uses_theory_practical:
            execute_query(
                """
                INSERT INTO subjects (name, code, sem_id, subject_type, theory_hours, practical_hours, lab_slots_per_session)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE name = VALUES(name), sem_id = VALUES(sem_id), subject_type = VALUES(subject_type),
                    theory_hours = VALUES(theory_hours), practical_hours = VALUES(practical_hours), lab_slots_per_session = VALUES(lab_slots_per_session)
                """,
                (name, code, sem_id, subject_type, th, pr, lab_slots or 2),
            )
        else:
            # Fallback for older schema shape
            room_type = "lab" if subject_type == "practical" else "theory"
            hours_per_week = 3 if not th else max(1, int(th / 16))
            execute_query(
                """
                INSERT INTO subjects (name, code, sem_id, subject_type, hours_per_week, lab_slots)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE name = VALUES(name), sem_id = VALUES(sem_id), subject_type = VALUES(subject_type),
                    hours_per_week = VALUES(hours_per_week), lab_slots = VALUES(lab_slots)
                """,
                (name, code, sem_id, room_type, hours_per_week, lab_slots or 2),
            )

    rows = execute_query("SELECT id, sem_id, code FROM subjects", fetch=True)
    return {(int(r["sem_id"]), r["code"]): int(r["id"]) for r in rows}


def seed_section_subject_teacher(
    section_ids: dict[tuple[int, str], int],
    subject_ids: dict[tuple[int, str], int],
    teacher_ids: dict[str, int],
    semester_ids: dict[tuple[str, int], int],
) -> None:
    cols = table_columns("section_subject_teacher")
    has_pair = "theory_teacher_id" in cols and "practical_teacher_id" in cols
    teacher_col = None
    if not has_pair:
        for c in ("teacher_id", "faculty_id", "staff_id"):
            if c in cols:
                teacher_col = c
                break
    if not has_pair and not teacher_col:
        raise RuntimeError("section_subject_teacher schema does not contain known teacher reference columns")

    cse3 = semester_ids[("CSE", 3)]
    cse5 = semester_ids[("CSE", 5)]
    ece3 = semester_ids[("ECE", 3)]
    me3 = semester_ids[("ME", 3)]

    # section key: (sem_id, section_name), subject key: (sem_id, subject_code)
    assignments = [
        ((cse3, "A"), (cse3, "CSE301"), "Dr. Aarav Sharma"),
        ((cse3, "A"), (cse3, "CSE302"), "Dr. Nisha Verma"),
        ((cse3, "A"), (cse3, "CSE3L1"), "Prof. Kiran Rao"),
        ((cse3, "A"), (cse3, "CSE303"), "Dr. Aarav Sharma"),
        ((cse3, "B"), (cse3, "CSE301"), "Dr. Nisha Verma"),
        ((cse3, "B"), (cse3, "CSE302"), "Dr. Aarav Sharma"),
        ((cse3, "B"), (cse3, "CSE3L1"), "Prof. Kiran Rao"),
        ((cse3, "B"), (cse3, "CSE303"), "Dr. Nisha Verma"),
        ((cse5, "A"), (cse5, "CSE501"), "Dr. Aarav Sharma"),
        ((ece3, "A"), (ece3, "ECE301"), "Dr. Meera Nair"),
        ((me3, "A"), (me3, "ME301"), "Prof. Rohan Das"),
    ]

    subject_meta = {r["id"]: r for r in execute_query("SELECT id, code, subject_type FROM subjects", fetch=True)}

    for sec_key, subj_key, teacher_name in assignments:
        section_id = section_ids.get(sec_key)
        subject_id = subject_ids.get(subj_key)
        teacher_id = teacher_ids.get(teacher_name)
        if not section_id or not subject_id or not teacher_id:
            continue

        if has_pair:
            subject_type = subject_meta[subject_id]["subject_type"]
            if subject_type == "theory":
                execute_query(
                    """
                    INSERT INTO section_subject_teacher (section_id, subject_id, theory_teacher_id, practical_teacher_id)
                    VALUES (%s, %s, %s, NULL)
                    ON DUPLICATE KEY UPDATE theory_teacher_id = VALUES(theory_teacher_id)
                    """,
                    (section_id, subject_id, teacher_id),
                )
            elif subject_type == "practical":
                execute_query(
                    """
                    INSERT INTO section_subject_teacher (section_id, subject_id, theory_teacher_id, practical_teacher_id)
                    VALUES (%s, %s, NULL, %s)
                    ON DUPLICATE KEY UPDATE practical_teacher_id = VALUES(practical_teacher_id)
                    """,
                    (section_id, subject_id, teacher_id),
                )
            else:
                execute_query(
                    """
                    INSERT INTO section_subject_teacher (section_id, subject_id, theory_teacher_id, practical_teacher_id)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE theory_teacher_id = VALUES(theory_teacher_id), practical_teacher_id = VALUES(practical_teacher_id)
                    """,
                    (section_id, subject_id, teacher_id, teacher_id),
                )
        else:
            execute_query(
                f"""
                INSERT INTO section_subject_teacher (section_id, subject_id, {teacher_col})
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE {teacher_col} = VALUES({teacher_col})
                """,
                (section_id, subject_id, teacher_id),
            )


def seed_smartclass_mapping(section_ids: dict[tuple[int, str], int], semester_ids: dict[tuple[str, int], int]) -> None:
    cols = table_columns("smartclassroom_class_section_map")
    if "smart_class_id" not in cols:
        return

    entries = [
        ("CS101-A", section_ids[(semester_ids[("CSE", 3)], "A")], "Synthetic demo mapping"),
        ("CS101-B", section_ids[(semester_ids[("CSE", 3)], "B")], "Synthetic demo mapping"),
        ("CS201-A", section_ids[(semester_ids[("CSE", 5)], "A")], "Synthetic demo mapping"),
    ]

    for class_id, section_id, notes in entries:
        execute_query(
            """
            INSERT INTO smartclassroom_class_section_map (smart_class_id, section_id, notes, is_active)
            VALUES (%s, %s, %s, 1)
            ON DUPLICATE KEY UPDATE section_id = VALUES(section_id), notes = VALUES(notes), is_active = 1
            """,
            (class_id, section_id, notes),
        )


def main() -> None:
    dept_ids = seed_departments()
    semester_ids = seed_semesters(dept_ids)
    section_ids = seed_sections(semester_ids)
    seed_rooms(dept_ids)
    teacher_ids = seed_teachers(dept_ids)
    seed_timeslots()
    subject_ids = seed_subjects(semester_ids)
    seed_section_subject_teacher(section_ids, subject_ids, teacher_ids, semester_ids)
    seed_smartclass_mapping(section_ids, semester_ids)

    print("Synthetic timetable seed completed successfully.")
    print("You can now open Scheduler > Generate and run timetable generation.")


if __name__ == "__main__":
    main()