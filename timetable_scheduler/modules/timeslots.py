# modules/timeslots.py
import streamlit as st
import pandas as pd
from db.connection import execute_query

def load_timeslots():
    return execute_query(
        "SELECT * FROM time_slots ORDER BY slot_number", fetch=True
    )

def page_timeslots():
    st.title("⏰ Time Slot Configuration")
    st.divider()

    tab1, tab2 = st.tabs(["📋 Current Slots", "➕ Add / Manage Slots"])

    # ── TAB 1: VIEW ─────────────────────────────────────────
    with tab1:
        slots = load_timeslots()
        if not slots:
            st.info("No time slots defined yet. Add them in the next tab.")
        else:
            df = pd.DataFrame(slots)[["slot_number","label","start_time","end_time","is_break"]]
            df["is_break"]   = df["is_break"].apply(lambda x: "🍽️ Break" if x else "📖 Period")
            df["start_time"] = df["start_time"].apply(lambda x: str(x) if x else "")
            df["end_time"]   = df["end_time"].apply(lambda x: str(x) if x else "")
            df.columns       = ["Slot #","Label","Start","End","Type"]
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Visual timeline
            st.subheader("🕐 Visual Day Timeline")
            for s in slots:
                start = str(s["start_time"])[:5] if s["start_time"] else ""
                end   = str(s["end_time"])[:5]   if s["end_time"]   else ""
                if s["is_break"]:
                    st.markdown(
                        f"<div style='background:#fff3cd;padding:6px 12px;"
                        f"border-radius:6px;margin:3px 0;border-left:4px solid #ffc107'>"
                        f"🍽️ <b>{s['label']}</b> &nbsp; {start} – {end} &nbsp; <i>(Break)</i></div>",
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f"<div style='background:#e8f4fd;padding:6px 12px;"
                        f"border-radius:6px;margin:3px 0;border-left:4px solid #2196F3'>"
                        f"📖 <b>{s['label']}</b> &nbsp; {start} – {end}</div>",
                        unsafe_allow_html=True
                    )

    # ── TAB 2: ADD / MANAGE ──────────────────────────────────
    with tab2:

        # Quick preset loader
        st.subheader("⚡ Quick Preset")
        st.caption("Load a common timetable structure instantly, then customize.")
        col1, col2 = st.columns([2, 1])
        preset = col1.selectbox("Choose Preset", [
            "-- Select --",
            "7 Periods (9AM–4PM with lunch)",
            "6 Periods (9AM–3PM with lunch)",
            "8 Periods (8AM–4PM with lunch)",
        ])
        if col2.button("Load Preset", use_container_width=True):
            presets = {
                "7 Periods (9AM–4PM with lunch)": [
                    (1,"Period 1","09:00","10:00",0),
                    (2,"Period 2","10:00","11:00",0),
                    (3,"Period 3","11:00","12:00",0),
                    (4,"Lunch Break","12:00","13:00",1),
                    (5,"Period 4","13:00","14:00",0),
                    (6,"Period 5","14:00","15:00",0),
                    (7,"Period 6","15:00","16:00",0),
                ],
                "6 Periods (9AM–3PM with lunch)": [
                    (1,"Period 1","09:00","10:00",0),
                    (2,"Period 2","10:00","11:00",0),
                    (3,"Period 3","11:00","12:00",0),
                    (4,"Lunch Break","12:00","13:00",1),
                    (5,"Period 4","13:00","14:00",0),
                    (6,"Period 5","14:00","15:00",0),
                ],
                "8 Periods (8AM–4PM with lunch)": [
                    (1,"Period 1","08:00","09:00",0),
                    (2,"Period 2","09:00","10:00",0),
                    (3,"Period 3","10:00","11:00",0),
                    (4,"Period 4","11:00","12:00",0),
                    (5,"Lunch Break","12:00","13:00",1),
                    (6,"Period 5","13:00","14:00",0),
                    (7,"Period 6","14:00","15:00",0),
                    (8,"Period 7","15:00","16:00",0),
                ],
            }
            if preset in presets:
                execute_query("DELETE FROM time_slots")
                for row in presets[preset]:
                    execute_query(
                        "INSERT INTO time_slots (slot_number,label,start_time,end_time,is_break) VALUES (%s,%s,%s,%s,%s)",
                        row
                    )
                st.success(f"✅ Preset '{preset}' loaded!")
                st.rerun()

        st.divider()

        # Manual add
        st.subheader("➕ Add Individual Slot")
        with st.form("add_slot"):
            col1, col2, col3, col4, col5 = st.columns(5)
            slot_num   = col1.number_input("Slot #", min_value=1, max_value=20, value=1)
            label      = col2.text_input("Label", placeholder="Period 1 / Lunch Break")
            start_time = col3.time_input("Start Time")
            end_time   = col4.time_input("End Time")
            is_break   = col5.checkbox("Is Break?")

            if st.form_submit_button("➕ Add Slot", use_container_width=True):
                if not label:
                    st.error("Label is required.")
                else:
                    try:
                        execute_query(
                            """INSERT INTO time_slots
                               (slot_number, label, start_time, end_time, is_break)
                               VALUES (%s,%s,%s,%s,%s)""",
                            (int(slot_num), label.strip(),
                             str(start_time), str(end_time), int(is_break))
                        )
                        st.success(f"✅ Slot '{label}' added!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error (duplicate slot #?): {e}")

        st.divider()

        # Edit / Delete
        st.subheader("✏️ Edit / Delete Slot")
        slots = load_timeslots()
        if slots:
            slot_labels = {f"#{s['slot_number']} {s['label']}": s for s in slots}
            sel = st.selectbox("Select Slot", list(slot_labels.keys()))
            if sel:
                s = slot_labels[sel]
                col1, col2, col3, col4, col5 = st.columns(5)
                new_num   = col1.number_input("Slot #", value=s["slot_number"],
                                              min_value=1, max_value=20, key="edit_slotnum")
                new_label = col2.text_input("Label", value=s["label"], key="edit_slotlabel")
                new_start = col3.time_input("Start", key="edit_slot_start")
                new_end   = col4.time_input("End",   key="edit_slot_end")
                new_break = col5.checkbox("Is Break?", value=bool(s["is_break"]),
                                          key="edit_slot_break")

                col_upd, col_del, col_clr = st.columns(3)
                if col_upd.button("💾 Update", use_container_width=True, key="upd_slot"):
                    try:
                        execute_query(
                            """UPDATE time_slots SET slot_number=%s, label=%s,
                               start_time=%s, end_time=%s, is_break=%s WHERE id=%s""",
                            (int(new_num), new_label, str(new_start),
                             str(new_end), int(new_break), s["id"])
                        )
                        st.success("✅ Updated!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

                if col_del.button("🗑️ Delete", use_container_width=True,
                                  key="del_slot", type="primary"):
                    execute_query("DELETE FROM time_slots WHERE id=%s", (s["id"],))
                    st.success("🗑️ Deleted!")
                    st.rerun()

                if col_clr.button("🧹 Clear ALL Slots", use_container_width=True,
                                  key="clr_slots"):
                    execute_query("DELETE FROM time_slots")
                    st.success("All slots cleared.")
                    st.rerun()