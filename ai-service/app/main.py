import numpy as np
import threading
import time
import uuid
from typing import Sequence

import requests
from fastapi import FastAPI, File, HTTPException, UploadFile

from app.core.settings import (
    BACKEND_SERVICE_URL,
    DB_HOST,
    DB_NAME,
    DB_PASSWORD,
    DB_PORT,
    DB_USER,
    DEVICE,
    EMBEDDINGS_FILE,
    FORWARD_ATTENDANCE,
    MATCH_THRESHOLD,
)
from app.schemas.contracts import (
    BatchRegisterResponse,
    HealthResponse,
    RecognizeResponse,
    RecognitionItem,
    RegisterResponse,
    TuningResponse,
)
from app.services.db_embedding_store import DBEmbeddingStore
from app.services.face_engine import FaceEngine
from app.services.image_io import decode_image_bytes

app = FastAPI(title="SmartClassroom AI Service", version="0.1.0")

store = DBEmbeddingStore(
    db_host=DB_HOST,
    db_port=DB_PORT,
    db_user=DB_USER,
    db_password=DB_PASSWORD,
    db_name=DB_NAME,
    json_fallback=EMBEDDINGS_FILE,
)
engine: FaceEngine | None = None
engine_error: str | None = None
_engine_lock = threading.Lock()


def _warmup_engine() -> None:
    global engine_error
    try:
        _ensure_engine()
    except Exception as exc:
        engine_error = str(exc)


def _ensure_engine() -> FaceEngine:
    global engine, engine_error
    if engine is not None:
        return engine

    with _engine_lock:
        if engine is not None:
            return engine

        engine_error = None
        try:
            engine = FaceEngine(DEVICE)
        except Exception as exc:  # pragma: no cover
            engine = None
            engine_error = str(exc)
            raise

    return engine


@app.on_event("startup")
def startup() -> None:
    # Keep startup non-blocking so /health can respond even when model download is slow.
    global engine_error
    engine_error = None
    threading.Thread(target=_warmup_engine, daemon=True).start()


def _require_engine() -> FaceEngine:
    try:
        return _ensure_engine()
    except Exception:
        raise HTTPException(status_code=503, detail=f"Model not ready: {engine_error}")


def _choose_threshold(override: float | None) -> float:
    if override is None:
        return MATCH_THRESHOLD
    if not 0.0 <= override <= 1.0:
        raise HTTPException(status_code=400, detail="threshold must be between 0.0 and 1.0")
    return override


def _forward_to_backend(matches: Sequence[RecognitionItem]) -> bool:
    payload = {
        "matches": [
            {
                "student_id": item.student_id,
                "similarity": item.similarity,
                "confidence": item.confidence,
            }
            for item in matches
        ],
        "source": "ai-service",
    }
    try:
        response = requests.post(
            f"{BACKEND_SERVICE_URL}/attendance/recognition",
            json=payload,
            timeout=5,
        )
        return 200 <= response.status_code < 300
    except Exception:
        return False


def _pose_hint_from_landmarks(landmarks: np.ndarray | None) -> str | None:
    if landmarks is None or len(landmarks) < 5:
        return None

    left_eye = landmarks[0]
    right_eye = landmarks[1]
    nose = landmarks[2]
    mouth_left = landmarks[3]
    mouth_right = landmarks[4]

    eye_center = (left_eye + right_eye) / 2.0
    mouth_center = (mouth_left + mouth_right) / 2.0
    face_height = max(1.0, float(mouth_center[1] - eye_center[1]))
    face_width = max(1.0, float(np.linalg.norm(right_eye - left_eye)))

    horizontal_offset = float((nose[0] - eye_center[0]) / face_width)
    vertical_offset = float((nose[1] - eye_center[1]) / face_height)

    if horizontal_offset > 0.20:
        return "look_right"
    if horizontal_offset < -0.20:
        return "look_left"
    if vertical_offset > 0.70:
        return "look_down"
    if vertical_offset < 0.35:
        return "look_up"
    return "center"


@app.get("/", response_model=HealthResponse)
def home() -> HealthResponse:
    return HealthResponse(
        status="AI service running",
        model_ready=engine is not None,
        registered_students=store.student_count(),
    )


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return home()


@app.post("/register-student", response_model=RegisterResponse)
async def register_student(student_id: str, image: UploadFile = File(...)) -> RegisterResponse:
    if not student_id.strip():
        raise HTTPException(status_code=400, detail="student_id is required")
    model = _require_engine()

    raw = await image.read()
    frame = decode_image_bytes(raw)
    faces = model.detect_faces(frame)
    if faces is None or len(faces) == 0:
        raise HTTPException(status_code=422, detail="No face detected")

    embedding = model.embedding(faces[0])
    samples = store.register(student_id=student_id.strip(), embedding=embedding)
    return RegisterResponse(
        student_id=student_id.strip(),
        samples=samples,
        message="Student embedding saved",
    )


@app.post("/register-student-batch", response_model=BatchRegisterResponse)
async def register_student_batch(student_id: str, images: list[UploadFile] = File(...)) -> BatchRegisterResponse:
    if not student_id.strip():
        raise HTTPException(status_code=400, detail="student_id is required")
    if not images:
        raise HTTPException(status_code=400, detail="at least one image is required")

    model = _require_engine()
    accepted = 0
    rejected = 0
    current_samples = store.get_samples(student_id.strip())

    for image in images:
        raw = await image.read()
        frame = decode_image_bytes(raw)
        faces = model.detect_faces(frame)
        if faces is None or len(faces) == 0:
            rejected += 1
            continue

        embedding = model.embedding(faces[0])
        current_samples = store.register(student_id=student_id.strip(), embedding=embedding)
        accepted += 1

    return BatchRegisterResponse(
        student_id=student_id.strip(),
        processed=len(images),
        accepted=accepted,
        rejected=rejected,
        samples=current_samples,
        message="Batch enrollment completed",
    )


@app.post("/enroll-face")
async def enroll_face(image: UploadFile = File(...)):
    """Enroll a face without a student_id (for faculty registration). Returns a unique face_identity_id."""
    model = _require_engine()

    raw = await image.read()
    frame = decode_image_bytes(raw)
    faces = model.detect_faces(frame)
    if faces is None or len(faces) == 0:
        raise HTTPException(status_code=422, detail="No face detected in image")

    embedding = model.embedding(faces[0])
    
    # Generate a unique face identity ID for faculty
    face_identity_id = f"FACE-{uuid.uuid4().hex[:12].upper()}"
    
    # Store the face embedding with generated ID
    samples = store.register(student_id=face_identity_id, embedding=embedding)
    
    return {
        "face_identity_id": face_identity_id,
        "samples": samples,
        "message": "Face enrolled successfully",
        "status": "success",
    }


@app.post("/enroll-face-batch")
async def enroll_face_batch(
    images: list[UploadFile] = File(...),
    face_identity_id: str | None = None,
):
    """Enroll faculty face with multiple angles, same technique as student batch enrollment."""
    if not images:
        raise HTTPException(status_code=400, detail="at least one image is required")

    model = _require_engine()
    resolved_face_id = (face_identity_id or "").strip() or f"FACE-{uuid.uuid4().hex[:12].upper()}"

    accepted = 0
    rejected = 0
    current_samples = store.get_samples(resolved_face_id)

    for image in images:
        raw = await image.read()
        frame = decode_image_bytes(raw)
        faces = model.detect_faces(frame)
        if faces is None or len(faces) == 0:
            rejected += 1
            continue

        embedding = model.embedding(faces[0])
        current_samples = store.register(student_id=resolved_face_id, embedding=embedding)
        accepted += 1

    if accepted == 0:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "No usable face detected in captured images",
                "processed": len(images),
                "accepted": accepted,
                "rejected": rejected,
            },
        )

    return {
        "face_identity_id": resolved_face_id,
        "processed": len(images),
        "accepted": accepted,
        "rejected": rejected,
        "samples": current_samples,
        "message": "Faculty batch enrollment completed",
        "status": "success",
    }


@app.post("/recognize", response_model=RecognizeResponse)
async def recognize(
    image: UploadFile = File(...),
    threshold: float | None = None,
    forward: bool = False,
    identity_prefix: str | None = None,
) -> RecognizeResponse:
    started = time.perf_counter()
    model = _require_engine()
    threshold_value = _choose_threshold(threshold)

    known = store.get_all()
    if identity_prefix:
        prefix = identity_prefix.strip()
        if prefix:
            known = {
                student_id: vector
                for student_id, vector in known.items()
                if student_id.startswith(prefix)
            }

    if not known:
        detail = "No registered identities found"
        if identity_prefix and identity_prefix.strip():
            detail = f"No registered identities found for prefix '{identity_prefix.strip()}'"
        raise HTTPException(status_code=409, detail=detail)

    raw = await image.read()
    frame = decode_image_bytes(raw)
    faces, boxes, landmarks = model.detect_faces_with_boxes(frame)
    if faces is None or len(faces) == 0:
        return RecognizeResponse(
            matches=[],
            total_faces=0,
            threshold_used=threshold_value,
            elapsed_ms=int((time.perf_counter() - started) * 1000),
            forwarded=False,
        )

    known_vectors = {
        student_id: np.array(vector, dtype=np.float32)
        for student_id, vector in known.items()
    }

    query_vectors = model.embeddings(faces)
    matches: list[RecognitionItem] = []
    for index, query in enumerate(query_vectors):
        best_id = None
        best_score = -1.0

        for student_id, vector in known_vectors.items():
            score = model.cosine_similarity(query, vector)
            if score > best_score:
                best_score = score
                best_id = student_id

        confidence = max(0.0, min(1.0, (best_score + 1.0) / 2.0))
        if best_score < threshold_value:
            best_id = None

        bbox = None
        if boxes is not None and index < len(boxes):
            box = boxes[index]
            bbox = [
                round(float(box[0]), 1),
                round(float(box[1]), 1),
                round(float(box[2]), 1),
                round(float(box[3]), 1),
            ]

        points = None
        pose_hint = None
        if landmarks is not None and index < len(landmarks):
            point_set = landmarks[index]
            points = [
                [round(float(point[0]), 1), round(float(point[1]), 1)]
                for point in point_set
            ]
            pose_hint = _pose_hint_from_landmarks(point_set)

        matches.append(
            RecognitionItem(
                student_id=best_id,
                similarity=round(best_score, 4),
                confidence=round(confidence, 4),
                bbox=bbox,
                landmarks=points,
                pose_hint=pose_hint,
            )
        )

    should_forward = forward or FORWARD_ATTENDANCE
    forwarded = _forward_to_backend(matches) if should_forward else False

    return RecognizeResponse(
        matches=matches,
        total_faces=len(matches),
        threshold_used=threshold_value,
        elapsed_ms=int((time.perf_counter() - started) * 1000),
        forwarded=forwarded,
    )


@app.post("/recognize-and-forward", response_model=RecognizeResponse)
async def recognize_and_forward(
    image: UploadFile = File(...),
    threshold: float | None = None,
) -> RecognizeResponse:
    return await recognize(image=image, threshold=threshold, forward=True)


@app.get("/tuning/thresholds", response_model=TuningResponse)
def tuning_thresholds() -> TuningResponse:
    return TuningResponse(
        recommended_match_threshold_individual=0.60,
        recommended_match_threshold_classroom=0.68,
        note="A score above 0.60 is treated as a positive match by default; use 0.68 in crowded classrooms to reduce false positives.",
    )
