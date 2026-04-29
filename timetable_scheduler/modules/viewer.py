# modules/viewer.py
import streamlit as st
import pandas as pd
from db.connection import execute_query
from config import WORKING_DAYS

# ════════════════════════════════════════════════════════════
#  DATA FETCHERS
# ════════════════════════════════════════════════════════════

def fetch_slots():
    return execute_query(
        "SELECT * FROM time_slots ORDER BY slot_number", fetch=True
    )

def fetch_timetable_for_section(section_id: int):
    return execute_query("""
        SELECT
            tt.day_of_week,
            tt.session_type,
            ts.slot_number,
            ts.label        AS slot_label,
            ts.start_time,
            ts.end_time,
            ts.is_break,
            sb.name         AS subject_name,
            sb.code         AS subject_code,
            sb.subject_type,
            t.full_name     AS teacher_name,
            r.name          AS room_name,
            r.room_type
        FROM timetable tt
        JOIN time_slots ts ON tt.slot_id    = ts.id
        JOIN subjects   sb ON tt.subject_id = sb.id
        JOIN teachers    t ON tt.teacher_id = t.id
        JOIN rooms       r ON tt.room_id    = r.id
        WHERE tt.section_id = %s
        ORDER BY ts.slot_number
    """, (section_id,), fetch=True)

def fetch_timetable_for_teacher(teacher_id: int):
    return execute_query("""
        SELECT
            tt.day_of_week,
            tt.session_type,
            ts.slot_number,
            ts.label        AS slot_label,
            ts.start_time,
            ts.end_time,
            sb.name         AS subject_name,
            sb.code         AS subject_code,
            sc.name         AS section_name,
            sm.sem_number,
            d.name          AS dept_name,
            r.name          AS room_name,
            r.room_type
        FROM timetable tt
        JOIN time_slots  ts ON tt.slot_id    = ts.id
        JOIN subjects    sb ON tt.subject_id = sb.id
        JOIN sections    sc ON tt.section_id = sc.id
        JOIN semesters   sm ON sc.sem_id     = sm.id
        JOIN departments  d ON sm.dept_id    = d.id
        JOIN rooms        r ON tt.room_id    = r.id
        WHERE tt.teacher_id = %s
        ORDER BY ts.slot_number
    """, (teacher_id,), fetch=True)

def fetch_all_sections_with_meta():
    return execute_query("""
        SELECT sc.id, sc.name AS section_name,
               sm.sem_number, sm.name AS sem_name,
               d.name AS dept_name, d.id AS dept_id
        FROM sections sc
        JOIN semesters sm ON sc.sem_id  = sm.id
        JOIN departments d ON sm.dept_id = d.id
        ORDER BY d.name, sm.sem_number, sc.name
    """, fetch=True)

def fetch_all_teachers():
    return execute_query("""
        SELECT t.id, t.full_name,
               COALESCE(d.name,'N/A') AS dept_name
        FROM teachers t
        LEFT JOIN departments d ON t.dept_id = d.id
        ORDER BY d.name, t.full_name
    """, fetch=True)


# ════════════════════════════════════════════════════════════
#  GRID BUILDER
# ════════════════════════════════════════════════════════════

def build_grid(rows: list, all_slots: list, cell_key: str) -> pd.DataFrame:
    """
    Builds a (slot × day) DataFrame.
    cell_key: what to display — 'section' or 'teacher' view differs slightly.
    """
    # Index: slot labels, Columns: days
    slot_labels = []
    for s in all_slots:
        t_start = str(s["start_time"])[:5] if s["start_time"] else ""
        t_end   = str(s["end_time"])[:5]   if s["end_time"]   else ""
        label   = f"{s['label']}\n{t_start}–{t_end}"
        slot_labels.append((s["slot_number"], label, bool(s["is_break"])))

    # Build lookup: {(day, slot_number): cell_text}
    lookup = {}
    for r in rows:
        day        = r["day_of_week"]
        slot_num   = r["slot_number"]
        is_lab     = r.get("session_type") == "lab" or r.get("room_type") == "lab"

        if cell_key == "section":
            line1 = r["subject_code"]
            line2 = r["teacher_name"].split()[0]   # first name only
            line3 = r["room_name"]
            tag   = "🔬" if is_lab else "📖"
            cell  = f"{tag} {line1}\n{line2}\n{line3}"
        else:  # teacher view
            line1 = r["subject_code"]
            line2 = f"Sec {r['section_name']} | Sem {r['sem_number']}"
            line3 = r["room_name"]
            tag   = "🔬" if is_lab else "📖"
            cell  = f"{tag} {line1}\n{line2}\n{line3}"

        # For lab — same slot may appear multiple times (consecutive), keep first
        if (day, slot_num) not in lookup:
            lookup[(day, slot_num)] = cell

    # Assemble DataFrame
    grid = {}
    for day in WORKING_DAYS:
        col = []
        for slot_num, slot_label, is_break in slot_labels:
            if is_break:
                col.append("🍽️ Break")
            else:
                col.append(lookup.get((day, slot_num), "—"))
        grid[day] = col

    index = [lbl for _, lbl, _ in slot_labels]
    return pd.DataFrame(grid, index=index)


# ════════════════════════════════════════════════════════════
#  STYLED HTML TABLE
# ════════════════════════════════════════════════════════════

def render_html_timetable(grid_df: pd.DataFrame, title: str):
    """Renders a beautiful color-coded HTML timetable."""

    day_colors = {
        "Monday":    "#4A90D9",
        "Tuesday":   "#7B68EE",
        "Wednesday": "#20B2AA",
        "Thursday":  "#FF8C00",
        "Friday":    "#C0392B",
    }

    html = f"""
    <style>
      .tt-wrap {{ overflow-x: auto; margin: 1rem 0; }}
      .tt-table {{
        border-collapse: collapse;
        width: 100%;
        font-family: 'Segoe UI', sans-serif;
        font-size: 0.82rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.12);
        border-radius: 10px;
        overflow: hidden;
      }}
      .tt-table th {{
        padding: 10px 14px;
        text-align: center;
        color: white;
        font-weight: 600;
        letter-spacing: 0.5px;
        font-size: 0.85rem;
      }}
      .tt-table td {{
        padding: 8px 10px;
        text-align: center;
        border: 1px solid #e0e0e0;
        vertical-align: middle;
        min-width: 110px;
        white-space: pre-line;
        line-height: 1.4;
      }}
      .tt-title {{
        font-size: 1.1rem;
        font-weight: 700;
        margin-bottom: 8px;
        color: #2c3e50;
      }}
      .slot-header {{
        background: #2c3e50 !important;
        color: white !important;
        font-weight: 600;
        min-width: 120px;
        text-align: left !important;
        padding-left: 12px !important;
      }}
      .cell-break {{
        background: #FFF9E6;
        color: #888;
        font-style: italic;
        font-size: 0.78rem;
      }}
      .cell-theory {{
        background: #EBF5FB;
        color: #1a4a6e;
      }}
      .cell-lab {{
        background: #EAFAF1;
        color: #145a32;
      }}
      .cell-empty {{
        background: #fafafa;
        color: #bbb;
      }}
    </style>
    <div class='tt-wrap'>
      <div class='tt-title'>📊 {title}</div>
      <table class='tt-table'>
        <thead>
          <tr>
            <th class='slot-header' style='background:#2c3e50'>Time Slot</th>
    """

    for day in grid_df.columns:
        color = day_colors.get(day, "#555")
        html += f"<th style='background:{color}'>{day}</th>"

    html += "</tr></thead><tbody>"

    for slot_label, row in grid_df.iterrows():
        # Clean slot label for display
        parts = slot_label.split("\n")
        slot_display = f"<b>{parts[0]}</b>"
        if len(parts) > 1:
            slot_display += f"<br><small style='color:#aaa'>{parts[1]}</small>"

        html += f"<tr><td class='slot-header'>{slot_display}</td>"

        for day in grid_df.columns:
            cell = row[day]
            if cell == "🍽️ Break":
                css = "cell-break"
            elif cell == "—":
                css = "cell-empty"
            elif "🔬" in cell:
                css = "cell-lab"
            else:
                css = "cell-theory"

            # Format cell content
            lines = cell.split("\n")
            formatted = "<br>".join(
                f"<b>{l}</b>" if i == 0 else f"<small>{l}</small>"
                for i, l in enumerate(lines)
            )
            html += f"<td class='{css}'>{formatted}</td>"

        html += "</tr>"

    html += "</tbody></table></div>"
    st.markdown(html, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
#  SUMMARY STATS FOR A SECTION
# ════════════════════════════════════════════════════════════

def render_section_stats(rows: list):
    if not rows:
        return
    theory = [r for r in rows if r.get("session_type") == "theory"]
    labs   = [r for r in rows if r.get("session_type") == "lab"]

    subjects = {}
    for r in rows:
        key = r["subject_code"]
        subjects.setdefault(key, {
            "name":    r["subject_name"],
            "code":    r["subject_code"],
            "teacher": r["teacher_name"],
            "type":    r.get("session_type","theory"),
            "count":   0
        })
        subjects[key]["count"] += 1

    col1, col2, col3 = st.columns(3)
    col1.metric("📖 Theory Periods / Week", len(theory))
    col2.metric("🔬 Lab Sessions / Week",   len(set(
        (r["day_of_week"], r["subject_code"]) for r in labs
    )))
    col3.metric("📚 Total Subjects", len(subjects))

    st.divider()
    st.subheader("📚 Subject Breakdown")
    df = pd.DataFrame(list(subjects.values()))
    df = df[["name","code","type","teacher","count"]]
    df.columns = ["Subject","Code","Type","Teacher","Periods/Week"]
    st.dataframe(df, use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════════
#  TEACHER WORKLOAD STATS
# ════════════════════════════════════════════════════════════

def render_teacher_stats(rows: list, teacher: dict):
    if not rows:
        return
    theory = [r for r in rows if r.get("session_type") == "theory"]
    labs   = [r for r in rows if r.get("session_type") == "lab"]
    days_active = len(set(r["day_of_week"] for r in rows))

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📖 Theory Periods",   len(theory))
    col2.metric("🔬 Lab Periods",       len(labs))
    col3.metric("⏱️ Total Hrs/Week",   len(theory) + len(labs))
    col4.metric("📅 Active Days",       days_active)

    max_hrs = teacher.get("max_hours_week", 20)
    total   = len(theory) + len(labs)
    load_pct = min(total / max_hrs, 1.0) if max_hrs > 0 else 0
    color = "normal" if load_pct < 0.85 else "inverse"
    st.progress(load_pct,
                text=f"Workload: {total}/{max_hrs} hrs/week ({load_pct*100:.0f}%)")

    st.divider()
    st.subheader("📋 Class Assignments")
    summary = {}
    for r in rows:
        key = (r["subject_code"], r["section_name"], r["sem_number"])
        summary.setdefault(key, {
            "Subject":  r["subject_name"],
            "Code":     r["subject_code"],
            "Section":  r["section_name"],
            "Sem":      r["sem_number"],
            "Dept":     r["dept_name"],
            "Type":     r.get("session_type","theory"),
            "Periods":  0
        })
        summary[key]["Periods"] += 1

    df = pd.DataFrame(list(summary.values()))
    st.dataframe(df, use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════════
#  MAIN PAGE
# ════════════════════════════════════════════════════════════

def page_viewer():
    st.title("📊 Timetable Viewer")
    st.divider()

    # Check if timetable exists
    count = execute_query(
        "SELECT COUNT(*) AS c FROM timetable", fetch=True
    )[0]["c"]
    if count == 0:
        st.warning("⚠️ No timetable generated yet. Go to ⚡ Generate first.")
        return

    all_slots = fetch_slots()

    # ── View mode tabs ──────────────────────────────────────
    tab1, tab2, tab3 = st.tabs([
        "🏫 Class-wise View",
        "👨‍🏫 Teacher-wise View",
        "🏛️ Department Overview"
    ])

    # ════════════════════════════════════════════════════════
    #  TAB 1 — CLASS-WISE
    # ════════════════════════════════════════════════════════
    with tab1:
        sections = fetch_all_sections_with_meta()
        if not sections:
            st.info("No sections found.")
            return

        # Department filter
        depts = sorted(set(s["dept_name"] for s in sections))
        col1, col2, col3 = st.columns(3)
        dept_sel = col1.selectbox("🏛️ Department", ["All"] + depts, key="v_dept")

        filtered_secs = sections if dept_sel == "All" else \
                        [s for s in sections if s["dept_name"] == dept_sel]

        sems = sorted(set(s["sem_number"] for s in filtered_secs))
        sem_sel = col2.selectbox(
            "📅 Semester",
            ["All"] + [f"Sem {s}" for s in sems],
            key="v_sem"
        )

        if sem_sel != "All":
            sem_num = int(sem_sel.split()[1])
            filtered_secs = [s for s in filtered_secs if s["sem_number"] == sem_num]

        sec_map = {
            f"{s['dept_name']} › Sem {s['sem_number']} › Section {s['section_name']}": s
            for s in filtered_secs
        }
        sel_sec = col3.selectbox("🗂️ Section", list(sec_map.keys()), key="v_sec")

        st.divider()

        if sel_sec:
            section = sec_map[sel_sec]
            rows = fetch_timetable_for_section(section["id"])

            if not rows:
                st.warning(f"No timetable entries found for this section.")
            else:
                # Header
                st.markdown(
                    f"### 🎓 {section['dept_name']} &nbsp;›&nbsp; "
                    f"Semester {section['sem_number']} &nbsp;›&nbsp; "
                    f"Section **{section['section_name']}**"
                )

                # Stats
                render_section_stats(rows)
                st.divider()

                # Grid
                grid_df = build_grid(rows, all_slots, cell_key="section")
                render_html_timetable(
                    grid_df,
                    f"Timetable — {section['dept_name']} | "
                    f"Sem {section['sem_number']} | Section {section['section_name']}"
                )

                # Legend
                st.markdown("""
                <div style='margin-top:1rem; font-size:0.8rem; color:#666'>
                  <b>Legend:</b> &nbsp;
                  <span style='background:#EBF5FB;padding:2px 8px;border-radius:4px'>📖 Theory</span> &nbsp;
                  <span style='background:#EAFAF1;padding:2px 8px;border-radius:4px'>🔬 Lab</span> &nbsp;
                  <span style='background:#FFF9E6;padding:2px 8px;border-radius:4px'>🍽️ Break</span> &nbsp;
                  <span style='background:#fafafa;padding:2px 8px;border-radius:4px'>— Free</span>
                </div>
                """, unsafe_allow_html=True)

                # Raw data expander
                with st.expander("🔍 View Raw Data"):
                    df = pd.DataFrame(rows)[[
                        "day_of_week","slot_label","subject_name",
                        "subject_code","session_type","teacher_name","room_name"
                    ]]
                    df.columns = ["Day","Slot","Subject","Code","Type","Teacher","Room"]
                    st.dataframe(df, use_container_width=True, hide_index=True)

    # ════════════════════════════════════════════════════════
    #  TAB 2 — TEACHER-WISE
    # ════════════════════════════════════════════════════════
    with tab2:
        teachers = fetch_all_teachers()
        if not teachers:
            st.info("No teachers found.")
            return

        t_depts = sorted(set(t["dept_name"] for t in teachers))
        col1, col2 = st.columns(2)
        t_dept_sel = col1.selectbox("🏛️ Department", ["All"] + t_depts, key="tv_dept")

        filtered_teachers = teachers if t_dept_sel == "All" else \
                            [t for t in teachers if t["dept_name"] == t_dept_sel]

        t_map = {
            f"{t['full_name']} ({t['dept_name']})": t
            for t in filtered_teachers
        }
        sel_teacher = col2.selectbox("👨‍🏫 Teacher", list(t_map.keys()), key="tv_teacher")

        st.divider()

        if sel_teacher:
            teacher = t_map[sel_teacher]
            rows    = fetch_timetable_for_teacher(teacher["id"])

            # Fetch max_hours for workload bar
            t_detail = execute_query(
                "SELECT max_hours_week FROM teachers WHERE id=%s",
                (teacher["id"],), fetch=True
            )
            teacher["max_hours_week"] = t_detail[0]["max_hours_week"] if t_detail else 20

            if not rows:
                st.warning("No timetable entries found for this teacher.")
            else:
                st.markdown(f"### 👨‍🏫 {teacher['full_name']} — {teacher['dept_name']}")
                render_teacher_stats(rows, teacher)
                st.divider()

                grid_df = build_grid(rows, all_slots, cell_key="teacher")
                render_html_timetable(
                    grid_df,
                    f"Timetable — {teacher['full_name']}"
                )

                with st.expander("🔍 View Raw Data"):
                    df = pd.DataFrame(rows)[[
                        "day_of_week","slot_label","subject_name",
                        "subject_code","session_type","section_name",
                        "sem_number","dept_name","room_name"
                    ]]
                    df.columns = ["Day","Slot","Subject","Code",
                                  "Type","Section","Sem","Dept","Room"]
                    st.dataframe(df, use_container_width=True, hide_index=True)

    # ════════════════════════════════════════════════════════
    #  TAB 3 — DEPARTMENT OVERVIEW
    # ════════════════════════════════════════════════════════
    with tab3:
        st.subheader("🏛️ Department-wise Timetable Summary")

        depts_all = execute_query(
            "SELECT * FROM departments ORDER BY name", fetch=True
        )
        if not depts_all:
            st.info("No departments found.")
            return

        for dept in depts_all:
            secs = [s for s in fetch_all_sections_with_meta()
                    if s["dept_id"] == dept["id"]]
            if not secs:
                continue

            with st.expander(
                f"🏛️ {dept['name']}  ({len(secs)} sections)", expanded=False
            ):
                # Sem-wise group
                sem_groups = {}
                for s in secs:
                    sem_groups.setdefault(s["sem_number"], []).append(s)

                for sem_num in sorted(sem_groups.keys()):
                    st.markdown(f"**📅 Semester {sem_num}**")
                    cols = st.columns(len(sem_groups[sem_num]))
                    for i, sec in enumerate(sem_groups[sem_num]):
                        rows = fetch_timetable_for_section(sec["id"])
                        theory = len([r for r in rows if r.get("session_type") == "theory"])
                        labs   = len(set(
                            (r["day_of_week"], r["subject_code"])
                            for r in rows if r.get("session_type") == "lab"
                        ))
                        cols[i].metric(
                            f"Section {sec['section_name']}",
                            f"{theory + labs} periods",
                            delta=f"T:{theory} L:{labs}"
                        )
                    st.divider()

        # Global fill summary
        st.subheader("📈 Overall Fill Summary")
        latest_log = execute_query("""
            SELECT * FROM generation_log
            ORDER BY generated_at DESC LIMIT 1
        """, fetch=True)

        if latest_log:
            log = latest_log[0]
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Last Generated", str(log["generated_at"])[:16])
            col2.metric("Status",         log["status"].upper())
            col3.metric("Fill Rate",
                        f"{log['filled_slots']}/{log['total_slots']}",
                        delta=f"{log['filled_slots']/log['total_slots']*100:.1f}%"
                              if log["total_slots"] > 0 else "N/A")
            col4.metric("Conflicts", log["conflict_count"],
                        delta_color="inverse" if log["conflict_count"] > 0 else "normal")