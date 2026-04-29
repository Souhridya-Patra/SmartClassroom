import pandas as pd
import streamlit as st

from db.connection import execute_query


def _load_sections():
    return execute_query(
        """
        SELECT
            sc.id,
            sc.name AS section_name,
            sm.sem_number,
            d.name AS dept_name
        FROM sections sc
        JOIN semesters sm ON sc.sem_id = sm.id
        JOIN departments d ON sm.dept_id = d.id
        ORDER BY d.name, sm.sem_number, sc.name
        """,
        fetch=True,
    )


def _load_mappings():
    return execute_query(
        """
        SELECT
            m.id,
            m.smart_class_id,
            m.section_id,
            m.notes,
            m.is_active,
            m.updated_at,
            sc.name AS section_name,
            sm.sem_number,
            d.name AS dept_name
        FROM smartclassroom_class_section_map m
        JOIN sections sc ON m.section_id = sc.id
        JOIN semesters sm ON sc.sem_id = sm.id
        JOIN departments d ON sm.dept_id = d.id
        ORDER BY m.smart_class_id
        """,
        fetch=True,
    )


def page_class_mapping():
    st.title("🔗 SmartClass Mapping")
    st.caption(
        "Bind SmartClassroom class IDs to scheduler sections. "
        "Backend session start uses this mapping first for timetable matching."
    )
    st.divider()

    sections = _load_sections()
    if not sections:
        st.warning("Please create departments, semesters, and sections first.")
        return

    section_labels = {
        f"{row['dept_name']} › Sem {row['sem_number']} › Section {row['section_name']}": row
        for row in sections
    }

    with st.expander("➕ Add / Update Mapping", expanded=True):
        with st.form("add_or_update_mapping"):
            col1, col2 = st.columns([2, 3])
            smart_class_id = col1.text_input(
                "SmartClassroom Class ID",
                placeholder="e.g. CS101-A",
            )
            section_choice = col2.selectbox("Map To Section", list(section_labels.keys()))
            notes = st.text_input("Notes (optional)", placeholder="Optional context")
            is_active = st.checkbox("Active", value=True)

            submitted = st.form_submit_button("Save Mapping", use_container_width=True)
            if submitted:
                class_id = (smart_class_id or "").strip()
                if not class_id:
                    st.error("Class ID is required.")
                else:
                    section_id = section_labels[section_choice]["id"]
                    execute_query(
                        """
                        INSERT INTO smartclassroom_class_section_map
                            (smart_class_id, section_id, notes, is_active)
                        VALUES (%s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            section_id = VALUES(section_id),
                            notes = VALUES(notes),
                            is_active = VALUES(is_active)
                        """,
                        (class_id, section_id, notes or None, int(is_active)),
                    )
                    st.success(f"Mapping saved for class '{class_id}'.")
                    st.rerun()

    st.subheader("📋 Current Mappings")
    mappings = _load_mappings()
    if not mappings:
        st.info("No mappings yet.")
        return

    df = pd.DataFrame(mappings)
    df = df[
        [
            "id",
            "smart_class_id",
            "dept_name",
            "sem_number",
            "section_name",
            "is_active",
            "updated_at",
            "notes",
        ]
    ]
    df.columns = [
        "ID",
        "Class ID",
        "Department",
        "Semester",
        "Section",
        "Active",
        "Updated",
        "Notes",
    ]
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("🧰 Manage Existing Mapping")

    mapping_labels = {
        f"{row['smart_class_id']} → {row['dept_name']} / Sem {row['sem_number']} / {row['section_name']}": row
        for row in mappings
    }
    selected_label = st.selectbox("Select mapping", list(mapping_labels.keys()))
    selected = mapping_labels[selected_label]

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        new_section_choice = st.selectbox(
            "Mapped Section",
            list(section_labels.keys()),
            index=next(
                (i for i, key in enumerate(section_labels.keys()) if section_labels[key]["id"] == selected["section_id"]),
                0,
            ),
            key="edit_map_section",
        )
    with col2:
        new_notes = st.text_input("Notes", value=selected.get("notes") or "", key="edit_map_notes")
    with col3:
        new_active = st.checkbox("Active", value=bool(selected.get("is_active")), key="edit_map_active")

    col_upd, col_del = st.columns(2)
    if col_upd.button("💾 Update Mapping", use_container_width=True):
        execute_query(
            """
            UPDATE smartclassroom_class_section_map
            SET section_id = %s, notes = %s, is_active = %s
            WHERE id = %s
            """,
            (section_labels[new_section_choice]["id"], new_notes or None, int(new_active), selected["id"]),
        )
        st.success("Mapping updated.")
        st.rerun()

    if col_del.button("🗑️ Delete Mapping", use_container_width=True, type="primary"):
        execute_query("DELETE FROM smartclassroom_class_section_map WHERE id = %s", (selected["id"],))
        st.success("Mapping deleted.")
        st.rerun()