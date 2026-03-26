from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    model_ready: bool
    registered_students: int


class RegisterResponse(BaseModel):
    student_id: str
    samples: int
    message: str


class BatchRegisterResponse(BaseModel):
    student_id: str
    processed: int
    accepted: int
    rejected: int
    samples: int
    message: str


class RecognitionItem(BaseModel):
    student_id: str | None
    similarity: float
    confidence: float
    bbox: list[float] | None = None
    landmarks: list[list[float]] | None = None
    pose_hint: str | None = None


class RecognizeResponse(BaseModel):
    matches: list[RecognitionItem]
    total_faces: int
    threshold_used: float
    elapsed_ms: int
    forwarded: bool = False


class TuningResponse(BaseModel):
    recommended_match_threshold_individual: float
    recommended_match_threshold_classroom: float
    note: str
