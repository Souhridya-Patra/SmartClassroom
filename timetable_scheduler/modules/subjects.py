# modules/subjects.py
import math
import streamlit as st
import pandas as pd
from db.connection import execute_query

# ── Helpers ──────────────────────────────────────────────────

def calc_theory_per_week(theory_hours, teaching_weeks):
    if not theory_hours or not teaching_weeks:
        return 0
    return math.ceil(theory_hours / teaching_weeks)

def calc_lab_sessions_per_week(practical_hours, teaching_weeks, slots_per_session):
    if not practical_hours or not teaching_weeks or not slots_per_session:
        return 0
    hours_per_week = math.ceil(practical_hours / teaching_weeks)
    return max(1, math.ceil(hours_per_week / slots_per_session))

def get_teaching_weeks(sem_id: int) -> int:
    rows = execute_query(
        "SELECT teaching_weeks FROM semesters WHERE id=%s",
        (sem_id,), fetch=True
    )
    return rows[0]["teaching_weeks"] if rows else 16

def load_subjects():
    return execute_query("""
        SELECT sb.id, sb.name, sb.code, sb.subject_type,
               sb.theory_hours, sb.practical_hours,
               sb.lab_slots_per_session,
               sm.id AS sem_id, sm.name AS sem_name,
               sm.sem_number, sm.teaching_weeks,
               d.name AS dept_name
        FROM subjects sb
        JOIN semesters sm ON sb.sem_id  = sm.id
        JOIN departments d ON sm.dept_id = d.id
        ORDER BY d.name, sm.sem_number, sb.subject_type, sb.name
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

# ── Page ─────────────────────────────────────────────────────

def page_subjects():
    st.title("📚 Subjects")
    st.divider()

    tab1, tab2, tab3 = st.tabs([
        "📋 View Subjects",
        "➕ Add / Edit Subject",
        "🔗 Assign Teacher to Section"
    ])

    # ════════════════════════════════════════════════════════
    #  TAB 1 — VIEW
    # ════════════════════════════════════════════════════════
    with tab1:
        subjects = load_subjects()
        if not subjects:
            st.info("No subjects yet. Add one in the next tab.")

        depts  = sorted(set(s["dept_name"] for s in subjects))
        dept_f = st.selectbox("Filter by Department",
                              ["All"] + depts, key="sub_dept_f")
        filtered = subjects if dept_f == "All" else \
                   [s for s in subjects if s["dept_name"] == dept_f]

        theory_only = [s for s in filtered if s["subject_type"] == "theory"]
        prac_only   = [s for s in filtered if s["subject_type"] == "practical"]
        both        = [s for s in filtered if s["subject_type"] == "theory+practical"]

        # Theory only
        st.subheader(f"📖 Theory Only  ({len(theory_only)})")
        if theory_only:
            rows = []
            for s in theory_only:
                wpw = calc_theory_per_week(
                    s["theory_hours"], s["teaching_weeks"]
                )
                rows.append({
                    "ID": s["id"], "Dept": s["dept_name"],
                    "Sem": s["sem_number"], "Name": s["name"],
                    "Code": s["code"],
                    "Total Theory Hrs": s["theory_hours"],
                    "Periods / Week": wpw
                })
            st.dataframe(pd.DataFrame(rows),
                         use_container_width=True, hide_index=True)
        else:
            st.caption("None added yet.")

        st.divider()

        # Practical only
        st.subheader(f"🔬 Practical Only  ({len(prac_only)})")
        if prac_only:
            rows = []
            for s in prac_only:
                spw = calc_lab_sessions_per_week(
                    s["practical_hours"], s["teaching_weeks"],
                    s["lab_slots_per_session"]
                )
                rows.append({
                    "ID": s["id"], "Dept": s["dept_name"],
                    "Sem": s["sem_number"], "Name": s["name"],
                    "Code": s["code"],
                    "Total Practical Hrs": s["practical_hours"],
                    "Slots / Session": s["lab_slots_per_session"],
                    "Sessions / Week": spw
                })
            st.dataframe(pd.DataFrame(rows),
                         use_container_width=True, hide_index=True)
        else:
            st.caption("None added yet.")

        st.divider()

        # Theory + Practical
        st.subheader(f"📖🔬 Theory + Practical  ({len(both)})")
        if both:
            rows = []
            for s in both:
                tpw = calc_theory_per_week(
                    s["theory_hours"], s["teaching_weeks"]
                )
                spw = calc_lab_sessions_per_week(
                    s["practical_hours"], s["teaching_weeks"],
                    s["lab_slots_per_session"]
                )
                rows.append({
                    "ID": s["id"], "Dept": s["dept_name"],
                    "Sem": s["sem_number"], "Name": s["name"],
                    "Code": s["code"],
                    "Theory Hrs (Total)": s["theory_hours"],
                    "Theory Periods/Week": tpw,
                    "Practical Hrs (Total)": s["practical_hours"],
                    "Lab Sessions/Week": spw,
                    "Slots/Session": s["lab_slots_per_session"]
                })
            st.dataframe(pd.DataFrame(rows),
                         use_container_width=True, hide_index=True)
        else:
            st.caption("None added yet.")

    # ════════════════════════════════════════════════════════
    #  TAB 2 — ADD / EDIT
    # ════════════════════════════════════════════════════════
    with tab2:
        sems = execute_query("""
            SELECT s.id, s.name, s.sem_number, s.teaching_weeks,
                   d.name AS dept_name
            FROM semesters s
            JOIN departments d ON s.dept_id = d.id
            WHERE EXISTS (
                SELECT 1
                FROM sections sc
                WHERE sc.sem_id = s.id
            )
            ORDER BY d.name, s.sem_number
        """, fetch=True)

        if not sems:
            st.warning("⚠️ Please add Sections first. Only semesters with sections are available here.")
            return

        sem_map = {
            f"{s['dept_name']} › Sem {s['sem_number']} ({s['name']})": s
            for s in sems
        }

        # ── Add form ─────────────────────────────────────────
        st.subheader("➕ Add New Subject")
        col1, col2, col3 = st.columns(3)
        sub_name = col1.text_input("Subject Name *", key="add_sub_name")
        sub_code = col2.text_input(
            "Subject Code *", placeholder="e.g. CS301", key="add_sub_code"
        )
        sem_sel = col3.selectbox("Semester *", list(sem_map.keys()), key="add_sub_sem")

        sem_obj = sem_map[sem_sel]
        teaching_weeks = sem_obj["teaching_weeks"]

        st.info(
            f"📅 This semester has **{teaching_weeks} teaching weeks**. "
            f"Hours/week will be auto-calculated from total hours entered below."
        )

        sub_type = st.selectbox(
            "Subject Type *",
            ["theory", "practical", "theory+practical"],
            key="add_sub_type",
            help=(
                "**theory** → only lectures in classroom  |  "
                "**practical** → only lab sessions  |  "
                "**theory+practical** → both, handled by same teacher"
            )
        )

        st.divider()

        # Dynamic fields based on type (reactive; updates immediately)
        col4, col5, col6 = st.columns(3)
        theory_hours = None
        practical_hours = None
        lab_slots_per_sess = 2

        if sub_type in ("theory", "theory+practical"):
            theory_hours = col4.number_input(
                "Total Theory Hours *",
                min_value=1, max_value=500, value=48,
                key="add_theory_hours",
                help="Total lecture hours across the full semester"
            )
            tpw = calc_theory_per_week(theory_hours, teaching_weeks)
            col4.caption(f"→ **{tpw} theory period(s) per week**")

        if sub_type in ("practical", "theory+practical"):
            practical_hours = col5.number_input(
                "Total Practical Hours *",
                min_value=1, max_value=500, value=32,
                key="add_practical_hours",
                help="Total lab hours across the full semester"
            )
            lab_slots_per_sess = col6.number_input(
                "Consecutive Slots / Lab Session",
                min_value=2, max_value=3, value=2,
                key="add_lab_slots",
                help="How many back-to-back periods each lab session uses"
            )
            spw = calc_lab_sessions_per_week(
                practical_hours, teaching_weeks, lab_slots_per_sess
            )
            col5.caption(
                f"→ **~{spw} lab session(s) per week** "
                f"({lab_slots_per_sess} slots each)"
            )

        if st.button("➕ Add Subject", use_container_width=True, key="btn_add_subject"):
            if not sub_name or not sub_code:
                st.error("Subject name and code are required.")
            elif sub_type in ("theory", "theory+practical") and not theory_hours:
                st.error("Theory hours are required.")
            elif sub_type in ("practical", "theory+practical") and not practical_hours:
                st.error("Practical hours are required.")
            else:
                try:
                    execute_query(
                        """INSERT INTO subjects
                           (name, code, sem_id, subject_type,
                            theory_hours, practical_hours,
                            lab_slots_per_session)
                           VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                        (sub_name.strip(),
                         sub_code.strip().upper(),
                         sem_obj["id"],
                         sub_type,
                         int(theory_hours) if theory_hours else None,
                         int(practical_hours) if practical_hours else None,
                         int(lab_slots_per_sess))
                    )
                    st.success(
                        f"✅ '{sub_name}' ({sub_type}) added! "
                        f"Sem: {sem_obj['name']}"
                    )
                    st.rerun()
                except Exception as e:
                    st.error(f"Error (duplicate code?): {e}")

        # ── Edit / Delete ─────────────────────────────────────
        st.divider()
        st.subheader("✏️ Edit / Delete Subject")
        all_subs = execute_query(
            "SELECT * FROM subjects ORDER BY name", fetch=True
        )
        if not all_subs:
            st.info("No subjects to edit yet.")
            return

        sub_labels = {
            f"{s['name']} ({s['code']}) [{s['subject_type']}]": s
            for s in all_subs
        }
        sel_sub = st.selectbox("Select Subject",
                               list(sub_labels.keys()), key="edit_sub_sel")

        if sel_sub:
            s = sub_labels[sel_sub]
            with st.form("edit_subject_form"):
                col1, col2 = st.columns(2)
                e_name = col1.text_input("Name", value=s["name"])
                e_code = col2.text_input("Code", value=s["code"])

                e_type = st.selectbox(
                    "Type",
                    ["theory", "practical", "theory+practical"],
                    index=["theory","practical","theory+practical"].index(
                        s["subject_type"]
                    )
                )

                col3, col4, col5 = st.columns(3)
                e_th = col3.number_input(
                    "Total Theory Hrs",
                    value=int(s["theory_hours"])    if s["theory_hours"]    else 0,
                    min_value=0
                )
                e_pr = col4.number_input(
                    "Total Practical Hrs",
                    value=int(s["practical_hours"]) if s["practical_hours"] else 0,
                    min_value=0
                )
                e_ls = col5.number_input(
                    "Lab Slots / Session",
                    value=int(s["lab_slots_per_session"])
                          if s["lab_slots_per_session"] else 2,
                    min_value=2, max_value=3
                )

                col_upd, col_del = st.columns(2)
                if col_upd.form_submit_button(
                    "💾 Update", use_container_width=True
                ):
                    try:
                        execute_query(
                            """UPDATE subjects
                               SET name=%s, code=%s, subject_type=%s,
                                   theory_hours=%s, practical_hours=%s,
                                   lab_slots_per_session=%s
                               WHERE id=%s""",
                            (e_name.strip(),
                             e_code.strip().upper(),
                             e_type,
                             int(e_th) if e_th else None,
                             int(e_pr) if e_pr else None,
                             int(e_ls),
                             s["id"])
                        )
                        st.success("✅ Subject updated!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

                if col_del.form_submit_button(
                    "🗑️ Delete", use_container_width=True
                ):
                    try:
                        execute_query(
                            "DELETE FROM subjects WHERE id=%s", (s["id"],)
                        )
                        st.success("🗑️ Deleted!")
                        st.rerun()
                    except Exception as e:
                        st.error(
                            f"Cannot delete — subject is assigned. Error: {e}"
                        )

    # ════════════════════════════════════════════════════════
    #  TAB 3 — ASSIGN TEACHER
    # ════════════════════════════════════════════════════════
    with tab3:
        st.subheader("🔗 Assign Teacher to Section–Subject")
        st.caption(
            "One teacher per subject–section. "
            "For Theory+Practical subjects, the same teacher "
            "handles both components."
        )

        mapping_cols = get_assignment_teacher_columns()
        single_teacher_col = None
        has_theory_col = "theory_teacher_id" in mapping_cols
        has_practical_col = "practical_teacher_id" in mapping_cols

        if not (has_theory_col and has_practical_col):
            # Fallback to legacy single-column schema variants
            for col in (
                "teacher_id", "faculty_id", "staff_id",
                "teacher", "faculty", "staff"
            ):
                if col in mapping_cols:
                    single_teacher_col = col
                    break

            if not single_teacher_col:
                for col in mapping_cols:
                    c = col.lower()
                    if any(k in c for k in ("teacher", "faculty", "staff")) and ("id" in c or "ref" in c):
                        single_teacher_col = col
                        break

        if not ((has_theory_col and has_practical_col) or single_teacher_col):
            st.error(
                "No teacher reference column found in section_subject_teacher. "
                "Expected theory_teacher_id/practical_teacher_id or a single teacher_id-like column."
            )
            return

        sems2 = execute_query("""
            SELECT s.id, s.name, s.sem_number, d.name AS dept_name
            FROM semesters s
            JOIN departments d ON s.dept_id = d.id
            WHERE EXISTS (
                SELECT 1
                FROM sections sc
                WHERE sc.sem_id = s.id
            )
            ORDER BY d.name, s.sem_number
        """, fetch=True)

        if not sems2:
            st.warning("No semesters with sections found.")
            return

        sem_map2 = {
            f"{s['dept_name']} › Sem {s['sem_number']}": s["id"]
            for s in sems2
        }
        sel_sem = st.selectbox("1️⃣ Semester",
                               list(sem_map2.keys()), key="assign_sem2")
        sem_id2 = sem_map2[sel_sem]

        sections = execute_query(
            "SELECT id, name FROM sections WHERE sem_id=%s ORDER BY name",
            (sem_id2,), fetch=True
        )
        subjects_in_sem = execute_query(
            """SELECT id, name, code, subject_type
               FROM subjects WHERE sem_id=%s ORDER BY name""",
            (sem_id2,), fetch=True
        )
        teachers_all = execute_query(
            "SELECT id, full_name FROM teachers ORDER BY full_name",
            fetch=True
        )

        if not sections:
            st.warning("No sections for this semester.")
        elif not subjects_in_sem:
            st.warning("No subjects for this semester.")
        elif not teachers_all:
            st.warning("No teachers found.")
        else:
            sec_map2 = {s["name"]: s["id"] for s in sections}
            sub_map2 = {
                f"{s['name']} ({s['code']}) [{s['subject_type']}]": s
                for s in subjects_in_sem
            }
            tchr_map = {t["full_name"]: t["id"] for t in teachers_all}

            with st.form("assign_teacher_form"):
                col1, col2, col3 = st.columns(3)
                sec_sel  = col1.selectbox("2️⃣ Section",
                                          list(sec_map2.keys()))
                sub_sel  = col2.selectbox("3️⃣ Subject",
                                          list(sub_map2.keys()))
                tchr_sel = col3.selectbox("4️⃣ Teacher",
                                          list(tchr_map.keys()))

                chosen_sub = sub_map2[sub_sel]

                # Info box based on subject type
                type_info = {
                    "theory":
                        "📖 Theory subject — teacher handles lectures only.",
                    "practical":
                        "🔬 Practical subject — teacher handles lab sessions only.",
                    "theory+practical":
                        "📖🔬 Theory+Practical — teacher handles "
                        "both lecture AND lab sessions."
                }
                st.info(type_info.get(chosen_sub["subject_type"], ""))

                if st.form_submit_button(
                    "🔗 Assign Teacher", use_container_width=True
                ):
                    try:
                        teacher_id = tchr_map[tchr_sel]
                        if has_theory_col and has_practical_col:
                            if chosen_sub["subject_type"] == "theory":
                                execute_query(
                                    """INSERT INTO section_subject_teacher
                                       (section_id, subject_id, theory_teacher_id, practical_teacher_id)
                                       VALUES (%s,%s,%s,NULL)
                                       ON DUPLICATE KEY UPDATE
                                         theory_teacher_id = VALUES(theory_teacher_id)""",
                                    (sec_map2[sec_sel], chosen_sub["id"], teacher_id)
                                )
                            elif chosen_sub["subject_type"] == "practical":
                                execute_query(
                                    """INSERT INTO section_subject_teacher
                                       (section_id, subject_id, theory_teacher_id, practical_teacher_id)
                                       VALUES (%s,%s,NULL,%s)
                                       ON DUPLICATE KEY UPDATE
                                         practical_teacher_id = VALUES(practical_teacher_id)""",
                                    (sec_map2[sec_sel], chosen_sub["id"], teacher_id)
                                )
                            else:
                                execute_query(
                                    """INSERT INTO section_subject_teacher
                                       (section_id, subject_id, theory_teacher_id, practical_teacher_id)
                                       VALUES (%s,%s,%s,%s)
                                       ON DUPLICATE KEY UPDATE
                                         theory_teacher_id = VALUES(theory_teacher_id),
                                         practical_teacher_id = VALUES(practical_teacher_id)""",
                                    (sec_map2[sec_sel], chosen_sub["id"], teacher_id, teacher_id)
                                )
                        else:
                            execute_query(
                                f"""INSERT INTO section_subject_teacher
                                   (section_id, subject_id, {single_teacher_col})
                                   VALUES (%s,%s,%s)
                                   ON DUPLICATE KEY UPDATE
                                     {single_teacher_col} = VALUES({single_teacher_col})""",
                                (sec_map2[sec_sel], chosen_sub["id"], teacher_id)
                            )
                        st.success(
                            f"✅ {tchr_sel} assigned to "
                            f"'{chosen_sub['name']}' for Section {sec_sel}!"
                        )
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

        # ── View assignments ──────────────────────────────────
        st.divider()
        st.subheader("📋 Current Assignments")
        if has_theory_col and has_practical_col:
            assignments = execute_query("""
                SELECT sst.id,
                       sc.name  AS section_name,
                       sb.name  AS subject_name,
                       sb.code  AS subject_code,
                       sb.subject_type,
                       CASE
                           WHEN sb.subject_type = 'theory' THEN tt.full_name
                           WHEN sb.subject_type = 'practical' THEN pt.full_name
                           ELSE COALESCE(tt.full_name, pt.full_name)
                       END AS teacher_name,
                       d.name       AS dept_name,
                       sm.sem_number
                FROM section_subject_teacher sst
                JOIN sections  sc ON sst.section_id = sc.id
                JOIN subjects  sb ON sst.subject_id = sb.id
                LEFT JOIN teachers tt ON sst.theory_teacher_id = tt.id
                LEFT JOIN teachers pt ON sst.practical_teacher_id = pt.id
                JOIN semesters sm ON sc.sem_id       = sm.id
                JOIN departments d ON sm.dept_id     = d.id
                ORDER BY d.name, sm.sem_number, sc.name, sb.subject_type
            """, fetch=True)
        else:
            assignments = execute_query(f"""
                SELECT sst.id,
                       sc.name  AS section_name,
                       sb.name  AS subject_name,
                       sb.code  AS subject_code,
                       sb.subject_type,
                       t.full_name  AS teacher_name,
                       d.name       AS dept_name,
                       sm.sem_number
                FROM section_subject_teacher sst
                JOIN sections  sc ON sst.section_id = sc.id
                JOIN subjects  sb ON sst.subject_id = sb.id
                JOIN teachers   t ON sst.{single_teacher_col} = t.id
                JOIN semesters sm ON sc.sem_id       = sm.id
                JOIN departments d ON sm.dept_id     = d.id
                ORDER BY d.name, sm.sem_number, sc.name, sb.subject_type
            """, fetch=True)

        if assignments:
            df = pd.DataFrame(assignments)[[
                "dept_name", "sem_number", "section_name",
                "subject_name", "subject_type", "teacher_name"
            ]]
            df.columns = ["Dept","Sem","Section",
                          "Subject","Type","Teacher"]
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Delete
            st.subheader("🗑️ Remove Assignment")
            raw = execute_query(
                "SELECT * FROM section_subject_teacher", fetch=True
            )
            del_map = {
                f"ID:{a['id']} | Sec:{a['section_id']} | Sub:{a['subject_id']}":
                    a["id"]
                for a in raw
            }
            del_sel = st.selectbox("Select to Remove",
                                   list(del_map.keys()), key="del_assign")
            if st.button("🗑️ Remove", type="primary", key="rm_assign"):
                execute_query(
                    "DELETE FROM section_subject_teacher WHERE id=%s",
                    (del_map[del_sel],)
                )
                st.success("Removed!")
                st.rerun()
        else:
            st.info("No assignments yet.")