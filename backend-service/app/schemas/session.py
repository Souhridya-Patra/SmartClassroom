from pydantic import BaseModel
from datetime import datetime

class SessionBase(BaseModel):
    professor_id: int
    start_time: datetime

class SessionCreate(SessionBase):
    pass

class Session(SessionBase):
    id: int
    end_time: datetime = None

    class Config:
        orm_mode = True

class SessionStart(BaseModel):
    professor_id: int
