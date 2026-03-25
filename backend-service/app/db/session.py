import os
import mysql.connector

def get_connection():
    conn = mysql.connector.connect(
        host="smart_db",          # ✅ Docker service name (IMPORTANT)
        user="root",
        password="root",
        database="smart_classroom"
    )
    return conn