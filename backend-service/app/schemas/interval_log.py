from pydantic import BaseModel
from datetime import datetime
from typing import List

class IntervalLogBase(BaseModel):
    session_id: int
    timestamp: datetime
    recognized_students: List[str]

class IntervalLogCreate(IntervalLogBase):
    pass

class IntervalLog(IntervalLogBase):
    id: int

    class Config:
        orm_mode = True
