from pydantic import BaseModel
from datetime import datetime

class AttendanceBase(BaseModel):
    session_id: int
    student_id: str
    timestamp: datetime

class AttendanceCreate(AttendanceBase):
    pass

class Attendance(AttendanceBase):
    id: int

    class Config:
        orm_mode = True
