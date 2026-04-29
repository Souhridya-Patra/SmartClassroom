# modules/teachers.py
import streamlit as st
import pandas as pd
from db.connection import execute_query
from modules.departments import load_departments
from config import WORKING_DAYS

def load_teachers():
    return execute_query("""
        SELECT t.id, t.full_name, t.email, t.max_hours_week,
               COALESCE(d.name, 'N/A') AS dept_name
        FROM teachers t
        LEFT JOIN departments d ON t.dept_id = d.id
        ORDER BY d.name, t.full_name
    """, fetch=True)

def get_teacher_availability(teacher_id: int) -> dict:
    """Returns {day: is_available} for a teacher."""
    rows = execute_query(
        "SELECT day_of_week, is_available FROM teacher_availability WHERE teacher_id=%s",
        (teacher_id,), fetch=True
    )
    avail = {day: True for day in WORKING_DAYS}   # default all available
    for r in rows:
        avail[r["day_of_week"]] = bool(r["is_available"])
    return avail

def save_teacher_availability(teacher_id: int, availability: dict):
    """Upserts availability rows for a teacher."""
    for day, is_avail in availability.items():
        existing = execute_query(
            "SELECT id FROM teacher_availability WHERE teacher_id=%s AND day_of_week=%s",
            (teacher_id, day), fetch=True
        )
        if existing:
            execute_query(
                "UPDATE teacher_availability SET is_available=%s WHERE teacher_id=%s AND day_of_week=%s",
                (int(is_avail), teacher_id, day)
            )
        else:
            execute_query(
                "INSERT INTO teacher_availability (teacher_id, day_of_week, is_available) VALUES (%s,%s,%s)",
                (teacher_id, day, int(is_avail))
            )

def page_teachers():
    st.title("👨‍🏫 Teachers & Faculty")
    st.divider()

    depts = load_departments()
    if not depts:
        st.warning("⚠️ Please add Departments first.")
        return

    dept_map = {"-- None --": None}
    dept_map.update({d["name"]: d["id"] for d in depts})

    # ── TABS ────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs(["📋 View All", "➕ Add Teacher", "✏️ Edit / Availability"])

    # ── TAB 1: VIEW ─────────────────────────────────────────
    with tab1:
        teachers = load_teachers()
        if not teachers:
            st.info("No teachers yet. Add one in the next tab.")
        else:
            st.subheader(f"Total Teachers: {len(teachers)}")

            # Group by department
            dept_groups = {}
            for t in teachers:
                dept_groups.setdefault(t["dept_name"], []).append(t)

            for dept, members in dept_groups.items():
                with st.expander(f"🏛️ {dept}  ({len(members)} teachers)", expanded=True):
                    df = pd.DataFrame(members)[["id","full_name","email","max_hours_week"]]
                    df.columns = ["ID","Full Name","Email","Max Hrs/Week"]
                    st.dataframe(df, use_container_width=True, hide_index=True)

    # ── TAB 2: ADD ──────────────────────────────────────────
    with tab2:
        with st.form("add_teacher"):
            st.subheader("Add New Teacher")
            col1, col2 = st.columns(2)
            full_name = col1.text_input("Full Name *")
            email     = col2.text_input("Email (optional)")
            col3, col4 = st.columns(2)
            dept_sel  = col3.selectbox("Department", list(dept_map.keys()))
            max_hrs   = col4.number_input("Max Teaching Hours/Week",
                                          min_value=1, max_value=40, value=20)

            st.markdown("**📅 Default Availability** *(uncheck days off)*")
            avail_cols = st.columns(5)
            default_avail = {}
            for i, day in enumerate(WORKING_DAYS):
                default_avail[day] = avail_cols[i].checkbox(day[:3], value=True, key=f"new_avail_{day}")

            if st.form_submit_button("➕ Add Teacher", use_container_width=True):
                if not full_name:
                    st.error("Full name is required.")
                else:
                    try:
                        teacher_id = execute_query(
                            "INSERT INTO teachers (full_name, email, dept_id, max_hours_week) VALUES (%s,%s,%s,%s)",
                            (full_name.strip(), email.strip() or None,
                             dept_map[dept_sel], int(max_hrs))
                        )
                        save_teacher_availability(teacher_id, default_avail)
                        st.success(f"✅ Teacher '{full_name}' added with availability saved!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

    # ── TAB 3: EDIT + AVAILABILITY ───────────────────────────
    with tab3:
        teachers = load_teachers()
        if not teachers:
            st.info("No teachers to edit.")
            return

        teacher_map = {f"{t['full_name']} — {t['dept_name']} (ID:{t['id']})": t
                       for t in teachers}
        sel = st.selectbox("Select Teacher", list(teacher_map.keys()))

        if sel:
            t = teacher_map[sel]
            st.divider()

            # Edit basic info
            st.subheader("✏️ Edit Basic Info")
            with st.form("edit_teacher"):
                col1, col2 = st.columns(2)
                new_name  = col1.text_input("Full Name", value=t["full_name"])
                new_email = col2.text_input("Email",     value=t["email"] or "")
                col3, col4 = st.columns(2)
                dept_keys = list(dept_map.keys())
                # find current dept in map
                curr_dept = next((k for k,v in dept_map.items() if v == execute_query(
                    "SELECT dept_id FROM teachers WHERE id=%s", (t["id"],), fetch=True
                )[0]["dept_id"]), "-- None --")
                new_dept  = col3.selectbox("Department", dept_keys,
                                           index=dept_keys.index(curr_dept),
                                           key="edit_t_dept")
                new_hrs   = col4.number_input("Max Hrs/Week", value=t["max_hours_week"],
                                              min_value=1, max_value=40)

                if st.form_submit_button("💾 Update Info", use_container_width=True):
                    try:
                        execute_query(
                            "UPDATE teachers SET full_name=%s, email=%s, dept_id=%s, max_hours_week=%s WHERE id=%s",
                            (new_name, new_email or None, dept_map[new_dept], int(new_hrs), t["id"])
                        )
                        st.success("✅ Teacher updated!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

            # Availability editor
            st.divider()
            st.subheader("📅 Edit Availability")
            current_avail = get_teacher_availability(t["id"])
            new_avail = {}
            avail_cols = st.columns(5)
            for i, day in enumerate(WORKING_DAYS):
                new_avail[day] = avail_cols[i].checkbox(
                    day, value=current_avail[day], key=f"avail_{t['id']}_{day}"
                )

            if st.button("💾 Save Availability", use_container_width=True):
                save_teacher_availability(t["id"], new_avail)
                st.success("✅ Availability saved!")

            st.divider()
            # Delete
            if st.button("🗑️ Delete This Teacher", type="primary", use_container_width=True):
                try:
                    execute_query("DELETE FROM teachers WHERE id=%s", (t["id"],))
                    st.success("🗑️ Teacher deleted.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Cannot delete — teacher assigned to subjects. Error: {e}")