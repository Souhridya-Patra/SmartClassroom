# modules/rooms.py
import streamlit as st
import pandas as pd
from db.connection import execute_query
from modules.departments import load_departments

def load_rooms():
    return execute_query("""
        SELECT r.id, r.name, r.room_type, r.capacity,
               COALESCE(d.name,'Shared') AS dept_name
        FROM rooms r
        LEFT JOIN departments d ON r.dept_id = d.id
        ORDER BY r.room_type, r.name
    """, fetch=True)

def page_rooms():
    st.title("🏠 Rooms & Labs")
    st.divider()

    depts = load_departments()
    dept_map = {"Shared (All Departments)": None}
    dept_map.update({d["name"]: d["id"] for d in depts})

    # ── ADD FORM ────────────────────────────────────────────
    with st.expander("➕ Add New Room / Lab", expanded=False):
        with st.form("add_room"):
            col1, col2 = st.columns(2)
            room_name = col1.text_input("Room Name *", placeholder="e.g. Room 101, Lab A")
            room_type = col2.selectbox("Room Type *", ["classroom", "lab"])
            col3, col4 = st.columns(2)
            capacity  = col3.number_input("Capacity", min_value=1, max_value=500, value=60)
            dept_sel  = col4.selectbox("Belongs To", list(dept_map.keys()))

            if st.form_submit_button("Add Room", use_container_width=True):
                if not room_name:
                    st.error("Room name is required.")
                else:
                    try:
                        execute_query(
                            "INSERT INTO rooms (name, room_type, capacity, dept_id) VALUES (%s,%s,%s,%s)",
                            (room_name.strip(), room_type, int(capacity), dept_map[dept_sel])
                        )
                        st.success(f"✅ Room '{room_name}' added!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

    # ── LIST ─────────────────────────────────────────────────
    rooms = load_rooms()
    if not rooms:
        st.info("No rooms yet.")
        return

    col1, col2 = st.columns(2)
    classrooms = [r for r in rooms if r["room_type"] == "classroom"]
    labs       = [r for r in rooms if r["room_type"] == "lab"]

    with col1:
        st.subheader(f"🏫 Classrooms ({len(classrooms)})")
        if classrooms:
            df = pd.DataFrame(classrooms)[["id","name","capacity","dept_name"]]
            df.columns = ["ID","Name","Capacity","Department"]
            st.dataframe(df, use_container_width=True, hide_index=True)

    with col2:
        st.subheader(f"🔬 Labs ({len(labs)})")
        if labs:
            df = pd.DataFrame(labs)[["id","name","capacity","dept_name"]]
            df.columns = ["ID","Name","Capacity","Department"]
            st.dataframe(df, use_container_width=True, hide_index=True)

    # ── EDIT / DELETE ───────────────────────────────────────
    st.subheader("✏️ Edit / Delete Room")
    raw = execute_query("SELECT * FROM rooms ORDER BY name", fetch=True)
    room_labels = {f"{r['name']} (ID:{r['id']})": r for r in raw}
    sel = st.selectbox("Select Room", list(room_labels.keys()))

    if sel:
        r = room_labels[sel]
        col1, col2, col3, col4 = st.columns(4)
        new_name = col1.text_input("Name", value=r["name"],     key="edit_rname")
        new_type = col2.selectbox("Type", ["classroom","lab"],
                                  index=["classroom","lab"].index(r["room_type"]),
                                  key="edit_rtype")
        new_cap  = col3.number_input("Capacity", value=r["capacity"],
                                     min_value=1, key="edit_rcap")
        new_dept = col4.selectbox("Department", list(dept_map.keys()), key="edit_rdept")

        col_upd, col_del = st.columns(2)
        if col_upd.button("💾 Update", use_container_width=True, key="upd_room"):
            try:
                execute_query(
                    "UPDATE rooms SET name=%s, room_type=%s, capacity=%s, dept_id=%s WHERE id=%s",
                    (new_name, new_type, int(new_cap), dept_map[new_dept], r["id"])
                )
                st.success("✅ Updated!")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

        if col_del.button("🗑️ Delete", use_container_width=True, key="del_room", type="primary"):
            try:
                execute_query("DELETE FROM rooms WHERE id=%s", (r["id"],))
                st.success("🗑️ Deleted!")
                st.rerun()
            except Exception as e:
                st.error(f"Cannot delete — room in use. Error: {e}")