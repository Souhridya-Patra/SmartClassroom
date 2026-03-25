from pydantic import BaseModel
from typing import List, Dict
from datetime import datetime

class StudentAttendance(BaseModel):
    id: str
    name: str
    timestamps: List[datetime]

class AttendanceReport(BaseModel):
    session_id: int
    report: List[StudentAttendance]
