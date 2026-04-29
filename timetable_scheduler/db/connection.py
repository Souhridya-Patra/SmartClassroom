# db/connection.py
import mysql.connector
from mysql.connector import Error
from config import DB_CONFIG

def get_connection():
    """Returns a live MySQL connection using WAMP config."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            return conn
    except Error as e:
        raise ConnectionError(f"❌ DB Connection failed: {e}")

def execute_query(query: str, params: tuple = (), fetch: bool = False):
    """
    Generic query executor.
    - fetch=False  → INSERT / UPDATE / DELETE  (returns lastrowid)
    - fetch=True   → SELECT                    (returns list of dicts)
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, params)
        if fetch:
            return cursor.fetchall()
        else:
            conn.commit()
            return cursor.lastrowid
    except Error as e:
        conn.rollback()
        raise RuntimeError(f"Query failed: {e}\nSQL: {query}")
    finally:
        cursor.close()
        conn.close()