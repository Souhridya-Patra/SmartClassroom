# app.py
import streamlit as st
from config import APP_TITLE
from db.connection import execute_query
from db.init_db import init_database
from modules.auth import init_admin, login_page, logout
from modules.departments import page_departments
from modules.semesters import page_semesters
from modules.sections import page_sections
from modules.rooms import page_rooms
from modules.teachers  import page_teachers
from modules.subjects  import page_subjects
from modules.timeslots import page_timeslots
from modules.class_mapping import page_class_mapping
from modules.generate_page import page_generate
from modules.viewer import page_viewer
from modules.export_page import page_export

# ── Page config ─────────────────────────────────────────────
st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Bootstrap admin on first run ────────────────────────────
init_database()
init_admin()

# ── Auth gate ───────────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    login_page()
    st.stop()

# ── Sidebar navigation ──────────────────────────────────────
with st.sidebar:
    st.markdown(f"### 🎓 {APP_TITLE}")
    st.caption(f"👤 Logged in as: **{st.session_state.get('admin_user','Admin')}**")
    st.divider()

    PAGES = {
        "📌 Dashboard":      "dashboard",
        "🏛️ Departments":    "departments",
        "📅 Semesters":      "semesters",
        "🗂️ Sections":       "sections",
        "🏠 Rooms & Labs":   "rooms",
        # ── Coming in next phases ──
        "👨‍🏫 Teachers":      "teachers",
        "📚 Subjects":       "subjects",
        "⏰ Time Slots":     "timeslots",
        "🔗 SmartClass Map": "class_mapping",
        "⚡ Generate":       "generate",
        "📊 View Timetable": "viewer",
        "📤 Export":         "export",
    }

    page = st.radio("Navigation", list(PAGES.keys()), label_visibility="collapsed")
    st.divider()
    if st.button("🚪 Logout", use_container_width=True):
        logout()

# ── Page router ─────────────────────────────────────────────
selected = PAGES[page]

if selected == "dashboard":
    st.title("📌 Dashboard")
    st.divider()
    # Quick stats
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🏛️ Departments", execute_query("SELECT COUNT(*) as c FROM departments", fetch=True)[0]["c"])
    col2.metric("📅 Semesters",   execute_query("SELECT COUNT(*) as c FROM semesters",   fetch=True)[0]["c"])
    col3.metric("🗂️ Sections",    execute_query("SELECT COUNT(*) as c FROM sections",    fetch=True)[0]["c"])
    col4.metric("🏠 Rooms",       execute_query("SELECT COUNT(*) as c FROM rooms",       fetch=True)[0]["c"])
    st.divider()
    st.info("👈 Use the sidebar to navigate. More stats will appear as you add data.")

elif selected == "departments":
    page_departments()

elif selected == "semesters":
    page_semesters()

elif selected == "sections":
    page_sections()

elif selected == "rooms":
    page_rooms()

elif selected == "teachers":
    page_teachers()

elif selected == "subjects":
    page_subjects()

elif selected == "timeslots":
    page_timeslots()

elif selected == "class_mapping":
    page_class_mapping()

elif selected == "generate":
    page_generate()

elif selected == "viewer":
    page_viewer()

elif selected == "export":
    page_export()

else:
    st.title(page)
    st.info("🚧 This module is coming in the next phase. Stay tuned!")