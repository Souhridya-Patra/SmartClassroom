import time
import mysql.connector
from app.core.config import settings

def get_connection():
    for i in range(10):
        try:
            conn = mysql.connector.connect(
                host=settings.DB_HOST,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                database=settings.DB_NAME
            )
            print("✅ Connected to MySQL")
            return conn
        except Exception as e:
            print(f"⏳ DB not ready... retrying ({i+1}/10)")
            time.sleep(3)
    raise Exception("❌ Could not connect to MySQL")
