from fastapi import FastAPI
from app.db.init_db import init
from db.session import get_connection

app = FastAPI()

@app.on_event("startup")
def startup():
    init()

@app.get("/")
def home():
    return {"message": "Backend running"}

@app.get("/health/db")
def db_health():
    conn = get_connection()
    conn.close()
    return {"status": "DB connected"}