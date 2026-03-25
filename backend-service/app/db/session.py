import mysql.connector
from mysql.connector import pooling
from app.core.config import settings

pool = None

def get_pool():
    global pool
    if pool is None:
        pool = pooling.MySQLConnectionPool(
            pool_name="smart_classroom_pool",
            pool_size=5,
            host=settings.DB_HOST,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME
        )
    return pool

def get_connection():
    conn = get_pool().get_connection()
    try:
        yield conn
    finally:
        conn.close()
