# modules/export_page.py
import streamlit as st
import pandas as pd
from db.connection import execute_query
from modules.exporter import (
    export_section_pdf,   export_teacher_pdf,
    export_section_excel, export_teacher_excel,
    export_all_sections_excel, export_all_teachers_excel
)

def page_export():
    st.title("📤 Export Timetables")
    st.divider()

    # Guard — no timetable yet
    count = execute_query(
        "SELECT COUNT(*) AS c FROM timetable", fetch=True
    )[0]["c"]
    if count == 0:
        st.warning("⚠️ No timetable generated yet. Go to ⚡ Generate first.")
        return

    tab1, tab2, tab3 = st.tabs([
        "🏫 Class-wise Export",
        "👨‍🏫 Teacher-wise Export",
        "📦 Bulk Export"
    ])

    # ════════════════════════════════════════════════════════
    #  TAB 1 — CLASS-WISE
    # ════════════════════════════════════════════════════════
    with tab1:
        st.subheader("Export Timetable for a Section")

        sections = execute_query("""
            SELECT sc.id, sc.name AS section_name,
                   sm.sem_number, d.name AS dept_name
            FROM sections sc
            JOIN semesters sm ON sc.sem_id  = sm.id
            JOIN departments d ON sm.dept_id = d.id
            ORDER BY d.name, sm.sem_number, sc.name
        """, fetch=True)

        if not sections:
            st.info("No sections found.")
        else:
            sec_map = {
                f"{s['dept_name']} › Sem {s['sem_number']} › Section {s['section_name']}": s
                for s in sections
            }

            col1, col2 = st.columns([3, 1])
            sel = col1.selectbox("Select Section", list(sec_map.keys()),
                                 key="exp_sec")
            fmt = col2.radio("Format", ["PDF", "Excel"], key="exp_sec_fmt",
                             horizontal=True)

            if st.button("⬇️ Download", use_container_width=True,
                         key="dl_sec", type="primary"):
                sec = sec_map[sel]
                with st.spinner("Generating file..."):
                    if fmt == "PDF":
                        data = export_section_pdf(sec["id"], sec)
                        fname = (f"Timetable_{sec['dept_name']}_"
                                 f"Sem{sec['sem_number']}_"
                                 f"Sec{sec['section_name']}.pdf")
                        mime = "application/pdf"
                    else:
                        data = export_section_excel(sec["id"], sec)
                        fname = (f"Timetable_{sec['dept_name']}_"
                                 f"Sem{sec['sem_number']}_"
                                 f"Sec{sec['section_name']}.xlsx")
                        mime = ("application/vnd.openxmlformats-"
                                "officedocument.spreadsheetml.sheet")

                st.download_button(
                    label    = f"📥 Save {fmt} — {fname}",
                    data     = data,
                    file_name= fname,
                    mime     = mime,
                    use_container_width=True
                )
                st.success(f"✅ {fmt} ready! Click above to save.")

            # Preview table
            st.divider()
            st.subheader("👁️ Quick Preview")
            if sel:
                sec = sec_map[sel]
                preview_rows = execute_query("""
                    SELECT tt.day_of_week, ts.label AS slot,
                           sb.code, sb.name AS subject,
                           tt.session_type, t.full_name AS teacher,
                           r.name AS room
                    FROM timetable tt
                    JOIN time_slots ts ON tt.slot_id    = ts.id
                    JOIN subjects   sb ON tt.subject_id = sb.id
                    JOIN teachers    t ON tt.teacher_id = t.id
                    JOIN rooms       r ON tt.room_id    = r.id
                    WHERE tt.section_id = %s
                    ORDER BY
                      FIELD(tt.day_of_week,
                        'Monday','Tuesday','Wednesday','Thursday','Friday'),
                      ts.slot_number
                """, (sec["id"],), fetch=True)

                if preview_rows:
                    df = pd.DataFrame(preview_rows)
                    df.columns = ["Day","Slot","Code","Subject",
                                  "Type","Teacher","Room"]
                    st.dataframe(df, use_container_width=True, hide_index=True)

    # ════════════════════════════════════════════════════════
    #  TAB 2 — TEACHER-WISE
    # ════════════════════════════════════════════════════════
    with tab2:
        st.subheader("Export Timetable for a Teacher")

        teachers = execute_query("""
            SELECT t.id, t.full_name,
                   COALESCE(d.name,'N/A') AS dept_name
            FROM teachers t
            LEFT JOIN departments d ON t.dept_id = d.id
            ORDER BY d.name, t.full_name
        """, fetch=True)

        if not teachers:
            st.info("No teachers found.")
        else:
            t_map = {
                f"{t['full_name']} ({t['dept_name']})": t
                for t in teachers
            }

            col1, col2 = st.columns([3, 1])
            t_sel = col1.selectbox("Select Teacher", list(t_map.keys()),
                                   key="exp_teacher")
            t_fmt = col2.radio("Format", ["PDF", "Excel"], key="exp_t_fmt",
                               horizontal=True)

            if st.button("⬇️ Download", use_container_width=True,
                         key="dl_teacher", type="primary"):
                teacher = t_map[t_sel]
                with st.spinner("Generating file..."):
                    if t_fmt == "PDF":
                        data  = export_teacher_pdf(
                            teacher["id"], teacher["full_name"]
                        )
                        fname = f"Timetable_{teacher['full_name'].replace(' ','_')}.pdf"
                        mime  = "application/pdf"
                    else:
                        data  = export_teacher_excel(
                            teacher["id"], teacher["full_name"]
                        )
                        fname = f"Timetable_{teacher['full_name'].replace(' ','_')}.xlsx"
                        mime  = ("application/vnd.openxmlformats-"
                                 "officedocument.spreadsheetml.sheet")

                st.download_button(
                    label    = f"📥 Save {t_fmt} — {fname}",
                    data     = data,
                    file_name= fname,
                    mime     = mime,
                    use_container_width=True
                )
                st.success(f"✅ {t_fmt} ready! Click above to save.")

            # Workload preview
            st.divider()
            st.subheader("📊 Workload Preview")
            if t_sel:
                teacher = t_map[t_sel]
                wl = execute_query("""
                    SELECT
                      tt.day_of_week AS Day,
                      COUNT(*) AS Periods,
                      SUM(tt.session_type='lab') AS Labs,
                      SUM(tt.session_type='theory') AS Theory
                    FROM timetable tt
                    WHERE tt.teacher_id = %s
                    GROUP BY tt.day_of_week
                    ORDER BY FIELD(tt.day_of_week,
                      'Monday','Tuesday','Wednesday','Thursday','Friday')
                """, (teacher["id"],), fetch=True)

                if wl:
                    df = pd.DataFrame(wl)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    total = sum(r["Periods"] for r in wl)
                    st.caption(f"**Total periods/week:** {total}")

    # ════════════════════════════════════════════════════════
    #  TAB 3 — BULK EXPORT
    # ════════════════════════════════════════════════════════
    with tab3:
        st.subheader("📦 Bulk Export — Entire Institute")
        st.info(
            "Downloads a single Excel workbook with one sheet "
            "per section or teacher. Perfect for printing everything at once."
        )

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 🏫 All Sections")
            st.caption("One sheet per section — all departments combined.")
            if st.button("⬇️ Download All Sections (Excel)",
                         use_container_width=True, key="bulk_sec"):
                with st.spinner("Compiling all section timetables..."):
                    data = export_all_sections_excel()
                st.download_button(
                    label     = "📥 Save — All_Sections_Timetable.xlsx",
                    data      = data,
                    file_name = "All_Sections_Timetable.xlsx",
                    mime      = ("application/vnd.openxmlformats-"
                                 "officedocument.spreadsheetml.sheet"),
                    use_container_width=True
                )

        with col2:
            st.markdown("#### 👨‍🏫 All Teachers")
            st.caption("One sheet per teacher — complete faculty workload.")
            if st.button("⬇️ Download All Teachers (Excel)",
                         use_container_width=True, key="bulk_teacher"):
                with st.spinner("Compiling all teacher timetables..."):
                    data = export_all_teachers_excel()
                st.download_button(
                    label     = "📥 Save — All_Teachers_Timetable.xlsx",
                    data      = data,
                    file_name = "All_Teachers_Timetable.xlsx",
                    mime      = ("application/vnd.openxmlformats-"
                                 "officedocument.spreadsheetml.sheet"),
                    use_container_width=True
                )

        # Export log summary
        st.divider()
        st.subheader("📜 Latest Generation Info")
        log = execute_query("""
            SELECT generated_at, status, total_slots,
                   filled_slots, conflict_count
            FROM generation_log
            ORDER BY generated_at DESC LIMIT 1
        """, fetch=True)

        if log:
            l = log[0]
            col1, col2, col3 = st.columns(3)
            col1.metric("Generated At", str(l["generated_at"])[:16])
            col2.metric("Fill Rate",
                        f"{l['filled_slots']}/{l['total_slots']}")
            col3.metric("Conflicts", l["conflict_count"],
                        delta_color="inverse"
                        if l["conflict_count"] > 0 else "normal")