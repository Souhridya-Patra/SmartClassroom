# modules/auth.py
import bcrypt
import streamlit as st
from db.connection import execute_query
from config import DEFAULT_ADMIN, DEFAULT_PASSWORD

# ── bootstrap: hash default password if placeholder exists ──
def init_admin():
    rows = execute_query("SELECT * FROM admin WHERE username = %s",
                         (DEFAULT_ADMIN,), fetch=True)
    if rows and rows[0]["password"] == "HASH_PLACEHOLDER":
        hashed = bcrypt.hashpw(DEFAULT_PASSWORD.encode(), bcrypt.gensalt()).decode()
        execute_query("UPDATE admin SET password = %s WHERE username = %s",
                      (hashed, DEFAULT_ADMIN))

def verify_login(username: str, password: str) -> bool:
    rows = execute_query("SELECT password FROM admin WHERE username = %s",
                         (username,), fetch=True)
    if not rows:
        return False
    return bcrypt.checkpw(password.encode(), rows[0]["password"].encode())

def login_page():
    """Renders the login form and manages session state."""
    st.markdown("""
        <div style='text-align:center; padding: 2rem 0 1rem'>
            <h1>🎓 Institute Timetable Scheduler</h1>
            <p style='color:gray'>Admin Portal</p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        with st.form("login_form"):
            st.subheader("🔐 Admin Login")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)

        if submitted:
            if verify_login(username, password):
                st.session_state["logged_in"] = True
                st.session_state["admin_user"] = username
                st.rerun()
            else:
                st.error("❌ Invalid username or password.")

def logout():
    st.session_state["logged_in"] = False
    st.session_state["admin_user"] = None
    st.rerun()