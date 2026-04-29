# modules/sections.py
import streamlit as st
import pandas as pd
from db.connection import execute_query

def load_sections():
    return execute_query("""
        SELECT sc.id, sc.name, sc.strength,
               sm.name AS sem_name, sm.sem_number,
               d.name  AS dept_name
        FROM sections sc
        JOIN semesters sm ON sc.sem_id = sm.id
        JOIN departments d ON sm.dept_id = d.id
        ORDER BY d.name, sm.sem_number, sc.name
    """, fetch=True)

def page_sections():
    st.title("🗂️ Sections")
    st.divider()

    sems = execute_query("""
        SELECT s.id, s.name, s.sem_number, d.name AS dept_name
        FROM semesters s JOIN departments d ON s.dept_id=d.id
        ORDER BY d.name, s.sem_number
    """, fetch=True)

    if not sems:
        st.warning("⚠️ Please add Semesters first.")
        return

    sem_map = {f"{s['dept_name']} › Sem {s['sem_number']} ({s['name']})": s["id"] for s in sems}

    # ── ADD FORM ────────────────────────────────────────────
    with st.expander("➕ Add New Section", expanded=False):
        with st.form("add_section"):
            col1, col2, col3 = st.columns(3)
            sem_label = col1.selectbox("Semester *", list(sem_map.keys()))
            sec_name  = col2.text_input("Section Name *", placeholder="A / B / C")
            strength  = col3.number_input("Student Strength", min_value=1, max_value=300, value=60)

            if st.form_submit_button("Add Section", use_container_width=True):
                if not sec_name:
                    st.error("Section name is required.")
                else:
                    try:
                        execute_query(
                            "INSERT INTO sections (sem_id, name, strength) VALUES (%s,%s,%s)",
                            (sem_map[sem_label], sec_name.strip().upper(), int(strength))
                        )
                        st.success(f"✅ Section '{sec_name}' added!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error (duplicate?): {e}")

    # ── LIST TABLE ──────────────────────────────────────────
    sections = load_sections()
    if not sections:
        st.info("No sections yet.")
        return

    st.subheader(f"📋 All Sections ({len(sections)})")
    df = pd.DataFrame(sections)[["id","dept_name","sem_name","name","strength"]]
    df.columns = ["ID","Department","Semester","Section","Strength"]
    st.dataframe(df, use_container_width=True, hide_index=True)

    # ── EDIT / DELETE ───────────────────────────────────────
    st.subheader("✏️ Edit / Delete Section")
    raw = execute_query("SELECT * FROM sections", fetch=True)
    sec_labels = {f"Section {s['name']} (ID:{s['id']})": s for s in raw}
    sel = st.selectbox("Select Section", list(sec_labels.keys()))

    if sel:
        s = sec_labels[sel]
        col1, col2, col3 = st.columns(3)
        new_sem   = col1.selectbox("Semester", list(sem_map.keys()),
                                   key="edit_sec_sem")
        new_name  = col2.text_input("Name", value=s["name"], key="edit_sec_name")
        new_str   = col3.number_input("Strength", value=s["strength"],
                                      min_value=1, max_value=300, key="edit_sec_str")

        col_upd, col_del = st.columns(2)
        if col_upd.button("💾 Update", use_container_width=True, key="upd_sec"):
            try:
                execute_query(
                    "UPDATE sections SET sem_id=%s, name=%s, strength=%s WHERE id=%s",
                    (sem_map[new_sem], new_name.strip().upper(), int(new_str), s["id"])
                )
                st.success("✅ Updated!")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

        if col_del.button("🗑️ Delete", use_container_width=True, key="del_sec", type="primary"):
            try:
                execute_query("DELETE FROM sections WHERE id=%s", (s["id"],))
                st.success("🗑️ Deleted!")
                st.rerun()
            except Exception as e:
                st.error(f"Cannot delete — has timetable entries. Error: {e}")