from pydantic import BaseModel
from typing import List

class RecognitionResult(BaseModel):
    session_id: int
    recognized_students: List[str]
