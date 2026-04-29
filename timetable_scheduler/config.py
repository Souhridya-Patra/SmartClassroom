import os

# config.py
# ─────────────────────────────────────────────
# Database configuration — environment driven so the app can run locally or in Docker
DB_CONFIG = {
    "host":     os.getenv("TIMETABLE_DB_HOST", os.getenv("DB_HOST", "localhost")),
    "port":     int(os.getenv("TIMETABLE_DB_PORT", os.getenv("DB_PORT", "3306"))),
    "user":     os.getenv("TIMETABLE_DB_USER", os.getenv("DB_USER", "root")),
    "password": os.getenv("TIMETABLE_DB_PASSWORD", os.getenv("DB_PASSWORD", "")),
    "database": os.getenv("TIMETABLE_DB_NAME", os.getenv("DB_NAME", "timetable_db"))
}

# App constants
APP_TITLE       = "Institute Timetable Scheduler"
WORKING_DAYS    = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
MAX_LAB_SLOTS   = 3     # max consecutive slots a lab can occupy
DEFAULT_ADMIN   = "admin"
DEFAULT_PASSWORD = "admin123"   # hashed on first run