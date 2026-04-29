# modules/scheduler.py
import math
import random
from db.connection import execute_query
from config import WORKING_DAYS

MAX_PERIODS_PER_DAY = 3

# ════════════════════════════════════════════════════════════
#  CALCULATORS
# ════════════════════════════════════════════════════════════

def calc_theory_per_week(theory_hours, teaching_weeks):
    if not theory_hours or not teaching_weeks:
        return 0
    return math.ceil(theory_hours / teaching_weeks)

def calc_lab_sessions_per_week(practical_hours, teaching_weeks,
                                slots_per_session):
    if not practical_hours or not teaching_weeks or not slots_per_session:
        return 0
    hours_pw = math.ceil(practical_hours / teaching_weeks)
    return max(1, math.ceil(hours_pw / slots_per_session))

# ════════════════════════════════════════════════════════════
#  DATA LOADERS
# ════════════════════════════════════════════════════════════

def load_all_sections():
    return execute_query("""
        SELECT sc.id, sc.name, sc.strength,
               sm.id AS sem_id, sm.sem_number, sm.teaching_weeks,
               d.id  AS dept_id, d.name AS dept_name
        FROM sections sc
        JOIN semesters sm ON sc.sem_id  = sm.id
        JOIN departments d ON sm.dept_id = d.id
        ORDER BY d.name, sm.sem_number, sc.name
    """, fetch=True)

def get_assignment_teacher_columns():
    cols = set()

    # Primary strategy: INFORMATION_SCHEMA
    try:
        rows = execute_query(
            """
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'section_subject_teacher'
            """,
            fetch=True
        )
        cols.update(r["COLUMN_NAME"] for r in rows)
    except Exception:
        pass

    # Fallback strategy: SHOW COLUMNS (works in stricter DB environments)
    if not cols:
        try:
            rows = execute_query("SHOW COLUMNS FROM section_subject_teacher", fetch=True)
            cols.update(r["Field"] for r in rows)
        except Exception:
            pass

    return cols

def load_assignments_for_section(section_id):
    mapping_cols = get_assignment_teacher_columns()
    has_theory_col = "theory_teacher_id" in mapping_cols
    has_practical_col = "practical_teacher_id" in mapping_cols

    if has_theory_col and has_practical_col:
        return execute_query("""
            SELECT CASE
                       WHEN sb.subject_type = 'theory' THEN sst.theory_teacher_id
                       WHEN sb.subject_type = 'practical' THEN sst.practical_teacher_id
                       ELSE COALESCE(sst.theory_teacher_id, sst.practical_teacher_id)
                   END                     AS teacher_id,
                   sb.id                   AS subject_id,
                   sb.name                 AS subject_name,
                   sb.code                 AS subject_code,
                   sb.subject_type,
                   sb.theory_hours,
                   sb.practical_hours,
                   sb.lab_slots_per_session,
                   sm.teaching_weeks
            FROM section_subject_teacher sst
            JOIN subjects  sb ON sst.subject_id = sb.id
            JOIN sections  sc ON sst.section_id = sc.id
            JOIN semesters sm ON sc.sem_id      = sm.id
            WHERE sst.section_id = %s
        """, (section_id,), fetch=True)

    teacher_col = None
    for col in (
        "teacher_id", "faculty_id", "staff_id",
        "teacher", "faculty", "staff"
    ):
        if col in mapping_cols:
            teacher_col = col
            break
    if not teacher_col:
        for col in mapping_cols:
            c = col.lower()
            if any(k in c for k in ("teacher", "faculty", "staff")) and ("id" in c or "ref" in c):
                teacher_col = col
                break

    if not teacher_col:
        return []

    return execute_query(f"""
        SELECT sst.{teacher_col}      AS teacher_id,
               sb.id                   AS subject_id,
               sb.name                 AS subject_name,
               sb.code                 AS subject_code,
               sb.subject_type,
               sb.theory_hours,
               sb.practical_hours,
               sb.lab_slots_per_session,
               sm.teaching_weeks
        FROM section_subject_teacher sst
        JOIN subjects  sb ON sst.subject_id = sb.id
        JOIN sections  sc ON sst.section_id = sc.id
        JOIN semesters sm ON sc.sem_id      = sm.id
        WHERE sst.section_id = %s
    """, (section_id,), fetch=True)

def load_slots():
    """Teaching slots only (no breaks)."""
    return execute_query(
        "SELECT * FROM time_slots WHERE is_break=0 ORDER BY slot_number",
        fetch=True
    )

def load_rooms():
    return execute_query(
        "SELECT * FROM rooms ORDER BY room_type, name", fetch=True
    )

def load_availability_map():
    rows = execute_query(
        "SELECT teacher_id, day_of_week, is_available "
        "FROM teacher_availability",
        fetch=True
    )
    avail = {}
    for r in rows:
        avail.setdefault(r["teacher_id"], {})
        avail[r["teacher_id"]][r["day_of_week"]] = bool(r["is_available"])
    return avail

# ════════════════════════════════════════════════════════════
#  CONSTRAINT CHECKERS
# ════════════════════════════════════════════════════════════

def teacher_free(tid, day, slot_id, booked):
    return not booked.get(("T", tid, day, slot_id), False)

def room_free(rid, day, slot_id, booked):
    return not booked.get(("R", rid, day, slot_id), False)

def section_free(sid, day, slot_id, booked):
    return not booked.get(("S", sid, day, slot_id), False)

def teacher_available(tid, day, avail_map):
    return avail_map.get(tid, {}).get(day, True)

def section_day_count(sid, day, booked, slots):
    return sum(
        1 for s in slots
        if booked.get(("S", sid, day, s["id"]), False)
    )

def get_consecutive(start_num, n, slots):
    teaching = sorted(slots, key=lambda x: x["slot_number"])
    window   = []
    for sl in teaching:
        if sl["slot_number"] >= start_num:
            window.append(sl)
            if len(window) == n:
                nums = [x["slot_number"] for x in window]
                if nums == list(range(nums[0], nums[0] + n)):
                    return window
                window = []
    return None

# ════════════════════════════════════════════════════════════
#  BOOKING
# ════════════════════════════════════════════════════════════

def book(section_id, teacher_id, room_id, day, slot_id, booked):
    booked[("T", teacher_id, day, slot_id)] = True
    booked[("R", room_id,    day, slot_id)] = True
    booked[("S", section_id, day, slot_id)] = True

def book_block(section_id, teacher_id, room_id, day, slots, booked):
    for sl in slots:
        book(section_id, teacher_id, room_id, day, sl["id"], booked)

# ════════════════════════════════════════════════════════════
#  SLOT FINDERS
# ════════════════════════════════════════════════════════════

def find_theory_slot(section_id, teacher_id, slots, rooms,
                     booked, avail_map):
    classrooms = [r for r in rooms if r["room_type"] == "classroom"] or rooms
    days = WORKING_DAYS[:]
    random.shuffle(days)
    sl_shuf = slots[:]
    random.shuffle(sl_shuf)

    for day in days:
        if not teacher_available(teacher_id, day, avail_map):
            continue
        if section_day_count(section_id, day, booked, slots) \
                >= MAX_PERIODS_PER_DAY:
            continue
        for sl in sl_shuf:
            if not section_free(section_id, day, sl["id"], booked):
                continue
            if not teacher_free(teacher_id, day, sl["id"], booked):
                continue
            for room in classrooms:
                if room_free(room["id"], day, sl["id"], booked):
                    return day, sl, room
    return None

def find_lab_slot(section_id, teacher_id, n_slots, slots,
                  rooms, booked, avail_map):
    labs = [r for r in rooms if r["room_type"] == "lab"] or rooms
    days = WORKING_DAYS[:]
    random.shuffle(days)
    slot_nums = sorted({s["slot_number"] for s in slots})

    for day in days:
        if not teacher_available(teacher_id, day, avail_map):
            continue
        for start in slot_nums:
            consec = get_consecutive(start, n_slots, slots)
            if not consec:
                continue
            all_free = all(
                section_free(section_id, day, sl["id"], booked) and
                teacher_free(teacher_id, day, sl["id"], booked)
                for sl in consec
            )
            if not all_free:
                continue
            for room in labs:
                if all(room_free(room["id"], day, sl["id"], booked)
                       for sl in consec):
                    return day, consec, room
    return None

# ════════════════════════════════════════════════════════════
#  DB WRITERS
# ════════════════════════════════════════════════════════════

def save_entry(gen_id, section_id, day, slot_id,
               subject_id, teacher_id, room_id, session_type):
    execute_query("""
        INSERT INTO timetable
          (gen_id, section_id, day_of_week, slot_id,
           subject_id, teacher_id, room_id, session_type)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    """, (gen_id, section_id, day, slot_id,
          subject_id, teacher_id, room_id, session_type))

def save_conflict(gen_id, section_id, subject_id, reason):
    execute_query("""
        INSERT INTO conflict_log
          (gen_id, section_id, subject_id, conflict_reason)
        VALUES (%s,%s,%s,%s)
    """, (gen_id, section_id, subject_id, reason))

# ════════════════════════════════════════════════════════════
#  MAIN SCHEDULER
# ════════════════════════════════════════════════════════════

def run_scheduler(max_retries=5, progress_callback=None):

    sections  = load_all_sections()
    slots     = load_slots()
    all_rooms = load_rooms()
    avail_map = load_availability_map()
    errors    = []

    # Pre-flight
    if not sections:
        return {"status": "failed", "error": "No sections found."}
    if not slots:
        return {"status": "failed", "error": "No time slots defined."}
    if not all_rooms:
        return {"status": "failed", "error": "No rooms found."}

    gen_id = execute_query("""
        INSERT INTO generation_log
          (status, total_slots, filled_slots, conflict_count)
        VALUES ('partial', 0, 0, 0)
    """)

    execute_query("DELETE FROM timetable")
    execute_query("DELETE FROM conflict_log")

    booked         = {}
    total_needed   = 0
    total_filled   = 0
    conflict_count = 0

    for sec_idx, section in enumerate(sections):
        if progress_callback:
            progress_callback(
                sec_idx / len(sections),
                f"Scheduling {section['dept_name']} › "
                f"Sem {section['sem_number']} › "
                f"Section {section['name']}"
            )

        assignments = load_assignments_for_section(section["id"])
        if not assignments:
            continue

        random.shuffle(assignments)

        for assign in assignments:
            sub_type       = assign["subject_type"]
            teaching_weeks = assign["teaching_weeks"] or 16
            subject_id     = assign["subject_id"]
            teacher_id     = assign["teacher_id"]
            lab_slots_n    = assign["lab_slots_per_session"] or 2

            if not teacher_id:
                msg = (f"No teacher assigned for "
                       f"'{assign['subject_name']}' "
                       f"in Section {section['name']}")
                errors.append(f"⚠️ {msg}")
                conflict_count += 1
                save_conflict(gen_id, section["id"], subject_id, msg)
                continue

            # ── THEORY component ─────────────────────────────
            if sub_type in ("theory", "theory+practical"):
                theory_pw  = calc_theory_per_week(
                    assign["theory_hours"], teaching_weeks
                )
                total_needed += theory_pw
                placed = 0

                for _ in range(max_retries * max(theory_pw, 1)):
                    if placed >= theory_pw:
                        break
                    result = find_theory_slot(
                        section["id"], teacher_id,
                        slots, all_rooms, booked, avail_map
                    )
                    if result:
                        day, sl, room = result
                        save_entry(gen_id, section["id"], day, sl["id"],
                                   subject_id, teacher_id,
                                   room["id"], "theory")
                        book(section["id"], teacher_id,
                             room["id"], day, sl["id"], booked)
                        placed      += 1
                        total_filled += 1
                    else:
                        break

                if placed < theory_pw:
                    msg = (f"Theory for '{assign['subject_name']}' "
                           f"Sec {section['name']}: "
                           f"placed {placed}/{theory_pw} periods/week")
                    errors.append(
                        f"⚠️ {section['dept_name']} Sem"
                        f"{section['sem_number']} › {msg}"
                    )
                    conflict_count += (theory_pw - placed)
                    save_conflict(gen_id, section["id"], subject_id, msg)

            # ── PRACTICAL component ──────────────────────────
            if sub_type in ("practical", "theory+practical"):
                lab_spw    = calc_lab_sessions_per_week(
                    assign["practical_hours"], teaching_weeks, lab_slots_n
                )
                total_needed += lab_spw
                placed = 0

                for _ in range(max_retries * max(lab_spw, 1)):
                    if placed >= lab_spw:
                        break
                    result = find_lab_slot(
                        section["id"], teacher_id, lab_slots_n,
                        slots, all_rooms, booked, avail_map
                    )
                    if result:
                        day, consec, room = result
                        for sl in consec:
                            save_entry(gen_id, section["id"], day,
                                       sl["id"], subject_id,
                                       teacher_id, room["id"], "lab")
                        book_block(section["id"], teacher_id,
                                   room["id"], day, consec, booked)
                        placed      += 1
                        total_filled += 1
                    else:
                        break

                if placed < lab_spw:
                    msg = (f"Lab for '{assign['subject_name']}' "
                           f"Sec {section['name']}: "
                           f"placed {placed}/{lab_spw} sessions/week")
                    errors.append(
                        f"⚠️ {section['dept_name']} Sem"
                        f"{section['sem_number']} › {msg}"
                    )
                    conflict_count += (lab_spw - placed)
                    save_conflict(gen_id, section["id"], subject_id, msg)

    # Finalise
    status = ("success"  if conflict_count == 0
              else "partial" if total_filled > 0
              else "failed")

    execute_query("""
        UPDATE generation_log
        SET status=%s, total_slots=%s, filled_slots=%s,
            conflict_count=%s, notes=%s
        WHERE id=%s
    """, (status, total_needed, total_filled, conflict_count,
          f"{len(errors)} conflicts" if errors else "Clean generation",
          gen_id))

    if progress_callback:
        progress_callback(1.0, "✅ Done!")

    return {
        "status":         status,
        "gen_id":         gen_id,
        "total_needed":   total_needed,
        "total_filled":   total_filled,
        "conflict_count": conflict_count,
        "errors":         errors
    }