# modules/departments.py
import streamlit as st
import pandas as pd
from db.connection import execute_query

def load_departments():
    return execute_query("SELECT * FROM departments ORDER BY name", fetch=True)

def page_departments():
    st.title("🏛️ Departments")
    st.divider()

    # ── ADD FORM ────────────────────────────────────────────
    with st.expander("➕ Add New Department", expanded=False):
        with st.form("add_dept"):
            col1, col2 = st.columns(2)
            name = col1.text_input("Department Name *")
            code = col2.text_input("Department Code *  (e.g. CSE, ECE)")
            if st.form_submit_button("Add Department", use_container_width=True):
                if not name or not code:
                    st.error("Both fields are required.")
                else:
                    try:
                        execute_query(
                            "INSERT INTO departments (name, code) VALUES (%s, %s)",
                            (name.strip(), code.strip().upper())
                        )
                        st.success(f"✅ Department '{name}' added!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

    # ── LIST TABLE ──────────────────────────────────────────
    depts = load_departments()
    if not depts:
        st.info("No departments yet. Add one above.")
        return

    st.subheader(f"📋 All Departments ({len(depts)})")
    df = pd.DataFrame(depts)[["id", "name", "code", "created_at"]]
    df.columns = ["ID", "Name", "Code", "Created At"]
    st.dataframe(df, use_container_width=True, hide_index=True)

    # ── EDIT / DELETE ───────────────────────────────────────
    st.subheader("✏️ Edit / Delete Department")
    dept_map = {f"{d['name']} ({d['code']})": d for d in depts}
    selected = st.selectbox("Select Department", list(dept_map.keys()))

    if selected:
        d = dept_map[selected]
        col1, col2 = st.columns(2)
        new_name = col1.text_input("Name", value=d["name"], key="edit_dname")
        new_code = col2.text_input("Code", value=d["code"], key="edit_dcode")

        col_upd, col_del = st.columns(2)
        if col_upd.button("💾 Update", use_container_width=True):
            try:
                execute_query(
                    "UPDATE departments SET name=%s, code=%s WHERE id=%s",
                    (new_name.strip(), new_code.strip().upper(), d["id"])
                )
                st.success("✅ Updated!")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

        if col_del.button("🗑️ Delete", use_container_width=True, type="primary"):
            try:
                execute_query("DELETE FROM departments WHERE id=%s", (d["id"],))
                st.success("🗑️ Deleted!")
                st.rerun()
            except Exception as e:
                st.error(f"Cannot delete — likely has linked semesters. Error: {e}")