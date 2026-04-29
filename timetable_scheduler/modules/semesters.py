# modules/semesters.py
import streamlit as st
import pandas as pd
from db.connection import execute_query
from modules.departments import load_departments

def load_semesters():
    return execute_query("""
        SELECT s.id, s.sem_number, s.name, s.teaching_weeks,
               d.name AS dept_name, d.id AS dept_id
        FROM semesters s
        JOIN departments d ON s.dept_id = d.id
        ORDER BY d.name, s.sem_number
    """, fetch=True)

def page_semesters():
    st.title("📅 Semesters")
    st.divider()

    depts = load_departments()
    if not depts:
        st.warning("⚠️ Please add Departments first.")
        return

    dept_map = {d["name"]: d["id"] for d in depts}

    # ── ADD ─────────────────────────────────────────────────
    with st.expander("➕ Add New Semester", expanded=False):
        with st.form("add_sem"):
            col1, col2, col3, col4 = st.columns(4)
            dept_name      = col1.selectbox("Department *", list(dept_map.keys()))
            sem_number     = col2.number_input("Semester Number *",
                                               min_value=1, max_value=12, step=1)
            sem_name       = col3.text_input("Label", placeholder="e.g. Semester 1")
            teaching_weeks = col4.number_input(
                "Teaching Weeks *", min_value=1, max_value=52, value=16,
                help="Total teaching weeks in this semester. Used to auto-calculate hrs/week."
            )
            if not sem_name:
                sem_name = f"Semester {int(sem_number)}"

            if st.form_submit_button("Add Semester", use_container_width=True):
                try:
                    execute_query(
                        """INSERT INTO semesters
                           (dept_id, name, sem_number, teaching_weeks)
                           VALUES (%s,%s,%s,%s)""",
                        (dept_map[dept_name], sem_name,
                         int(sem_number), int(teaching_weeks))
                    )
                    st.success(f"✅ {sem_name} added! ({teaching_weeks} teaching weeks)")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error (duplicate?): {e}")

    # ── LIST ────────────────────────────────────────────────
    sems = load_semesters()
    if not sems:
        st.info("No semesters yet.")
        return

    st.subheader(f"📋 All Semesters ({len(sems)})")
    df = pd.DataFrame(sems)[["id","dept_name","sem_number","name","teaching_weeks"]]
    df.columns = ["ID","Department","Sem No.","Label","Teaching Weeks"]
    st.dataframe(df, use_container_width=True, hide_index=True)

    # ── EDIT / DELETE ────────────────────────────────────────
    st.subheader("✏️ Edit / Delete Semester")
    raw = execute_query("SELECT * FROM semesters ORDER BY dept_id, sem_number", fetch=True)
    sem_labels = {f"Sem {s['sem_number']} — {s['name']} (ID:{s['id']})": s for s in raw}
    sel = st.selectbox("Select Semester", list(sem_labels.keys()))

    if sel:
        s = sem_labels[sel]
        col1, col2, col3, col4 = st.columns(4)
        dept_keys = list(dept_map.keys())
        curr_dept = next(
            (k for k, v in dept_map.items() if v == s["dept_id"]), dept_keys[0]
        )
        new_dept  = col1.selectbox("Department", dept_keys,
                                   index=dept_keys.index(curr_dept), key="edit_sem_dept")
        new_num   = col2.number_input("Sem No.", value=s["sem_number"],
                                      min_value=1, max_value=12, key="edit_sem_num")
        new_label = col3.text_input("Label", value=s["name"], key="edit_sem_label")
        new_weeks = col4.number_input("Teaching Weeks", value=s["teaching_weeks"],
                                      min_value=1, max_value=52, key="edit_sem_weeks")

        col_upd, col_del = st.columns(2)
        if col_upd.button("💾 Update", use_container_width=True, key="upd_sem"):
            try:
                execute_query(
                    """UPDATE semesters
                       SET dept_id=%s, sem_number=%s, name=%s, teaching_weeks=%s
                       WHERE id=%s""",
                    (dept_map[new_dept], int(new_num),
                     new_label, int(new_weeks), s["id"])
                )
                st.success("✅ Updated!")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

        if col_del.button("🗑️ Delete", use_container_width=True,
                          key="del_sem", type="primary"):
            try:
                execute_query("DELETE FROM semesters WHERE id=%s", (s["id"],))
                st.success("🗑️ Deleted!")
                st.rerun()
            except Exception as e:
                st.error(f"Cannot delete — has linked sections. Error: {e}")