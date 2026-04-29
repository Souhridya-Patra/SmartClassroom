# modules/generate_page.py
import streamlit as st
import pandas as pd
from modules.scheduler import run_scheduler
from db.connection import execute_query

def page_generate():
    st.title("⚡ Generate Timetable")
    st.divider()

    # ── Pre-flight summary ─────────────────────────────────
    st.subheader("📋 Pre-Generation Checklist")

    checks = {
        "🏛️ Departments":            execute_query("SELECT COUNT(*) AS c FROM departments",              fetch=True)[0]["c"],
        "📅 Semesters":              execute_query("SELECT COUNT(*) AS c FROM semesters",                fetch=True)[0]["c"],
        "🗂️ Sections":               execute_query("SELECT COUNT(*) AS c FROM sections",                 fetch=True)[0]["c"],
        "👨‍🏫 Teachers":              execute_query("SELECT COUNT(*) AS c FROM teachers",                 fetch=True)[0]["c"],
        "📚 Subjects":               execute_query("SELECT COUNT(*) AS c FROM subjects",                 fetch=True)[0]["c"],
        "🔗 Teacher Assignments":    execute_query("SELECT COUNT(*) AS c FROM section_subject_teacher",  fetch=True)[0]["c"],
        "🏠 Rooms":                  execute_query("SELECT COUNT(*) AS c FROM rooms",                    fetch=True)[0]["c"],
        "⏰ Time Slots":             execute_query("SELECT COUNT(*) AS c FROM time_slots WHERE is_break=0", fetch=True)[0]["c"],
    }

    all_ready = True
    cols = st.columns(4)
    for i, (label, count) in enumerate(checks.items()):
        ready = count > 0
        if not ready:
            all_ready = False
        cols[i % 4].metric(
            label,
            count,
            delta="✅ Ready" if ready else "❌ Missing",
            delta_color="normal" if ready else "inverse"
        )

    st.divider()

    if not all_ready:
        st.error("❌ Some required data is missing. Please complete all sections above before generating.")
        return

    # ── Settings ───────────────────────────────────────────
    st.subheader("⚙️ Scheduler Settings")
    col1, col2 = st.columns(2)
    max_retries = col1.slider(
        "Max Retry Attempts per Subject",
        min_value=3, max_value=20, value=5,
        help="Higher = more thorough but slower. 5 is recommended."
    )
    col2.info(
        "🔄 Each run clears the previous timetable and generates fresh. "
        "You can re-run as many times as needed."
    )

    st.divider()

    # ── Generate button ────────────────────────────────────
    st.subheader("🚀 Run Scheduler")
    if st.button("⚡ Generate Timetable Now", type="primary",
                 use_container_width=True):

        progress_bar  = st.progress(0, text="Initialising scheduler...")
        status_text   = st.empty()
        result_holder = st.empty()

        def update_progress(pct, msg):
            progress_bar.progress(pct, text=msg)
            status_text.caption(msg)

        with st.spinner("Running constraint-based scheduler..."):
            result = run_scheduler(
                max_retries=max_retries,
                progress_callback=update_progress
            )

        progress_bar.empty()
        status_text.empty()

        # ── Result display ─────────────────────────────────
        with result_holder.container():
            st.divider()
            if result["status"] == "failed":
                st.error(f"❌ Generation failed: {result.get('error','Unknown error')}")
                return

            # Stats
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Status",
                        "✅ Clean" if result["status"] == "success" else "⚠️ Partial",
                        delta=result["status"].upper())
            col2.metric("Slots Needed",   result["total_needed"])
            col3.metric("Slots Filled",   result["total_filled"])
            col4.metric("Conflicts",      result["conflict_count"],
                        delta_color="inverse" if result["conflict_count"] > 0 else "normal")

            fill_pct = (result["total_filled"] / result["total_needed"] * 100) \
                       if result["total_needed"] > 0 else 0
            st.progress(int(fill_pct) / 100,
                        text=f"Fill Rate: {fill_pct:.1f}%")

            if result["status"] == "success":
                st.success("🎉 Timetable generated successfully with zero conflicts!")
            else:
                st.warning(
                    f"⚠️ Timetable partially generated. "
                    f"{result['conflict_count']} slot(s) could not be filled."
                )

            # Conflict details
            if result["errors"]:
                with st.expander(f"🔍 View {len(result['errors'])} Conflict(s)", expanded=True):
                    for err in result["errors"]:
                        st.warning(err)
                    st.caption(
                        "💡 Tip: Add more rooms/labs, reduce hours/week, "
                        "or check teacher availability to resolve conflicts."
                    )

    st.divider()

    # ── Generation History ─────────────────────────────────
    st.subheader("📜 Generation History")
    logs = execute_query("""
        SELECT id, generated_at, status,
               total_slots, filled_slots, conflict_count, notes
        FROM generation_log
        ORDER BY generated_at DESC
        LIMIT 10
    """, fetch=True)

    if logs:
        df = pd.DataFrame(logs)
        df["fill_rate"] = df.apply(
            lambda r: f"{r['filled_slots']/r['total_slots']*100:.1f}%"
                      if r["total_slots"] > 0 else "N/A",
            axis=1
        )
        df = df[["id","generated_at","status","total_slots","filled_slots","fill_rate","conflict_count","notes"]]
        df.columns = ["Run ID","Generated At","Status","Needed","Filled","Fill Rate","Conflicts","Notes"]

        def highlight_status(row):
            if row["Status"] == "success":
                return ["background-color: #d4edda"] * len(row)
            elif row["Status"] == "partial":
                return ["background-color: #fff3cd"] * len(row)
            return ["background-color: #f8d7da"] * len(row)

        st.dataframe(
            df.style.apply(highlight_status, axis=1),
            use_container_width=True, hide_index=True
        )
    else:
        st.info("No generation runs yet. Click Generate above!")