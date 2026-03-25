from fastapi import FastAPI, File, UploadFile, Form
from PIL import Image
from typing import List
import requests

from .services.face_detector import FaceDetector
from .services.embedding_generator import EmbeddingGenerator
from .services.matcher import Matcher
from .services.registration_service import RegistrationService

app = FastAPI()

# In-memory "database" to store student embeddings.
student_embeddings = {}

# Initialize services
face_detector = FaceDetector()
embedding_generator = EmbeddingGenerator()
registration_service = RegistrationService(student_embeddings, face_detector, embedding_generator)
matcher = Matcher(student_embeddings)


@app.get("/")
def home():
    return {"message": "AI service running"}

@app.post("/register")
async def register(student_id: str, files: List[UploadFile] = File(...)):
    success = registration_service.register_student(student_id, [f.file for f in files])
    if success:
        return {"message": f"Student {student_id} registered successfully."}
    return {"message": f"Could not register student {student_id}. No faces found in the provided images."}

@app.post("/recognize")
async def recognize(session_id: int = Form(...), file: UploadFile = File(...)):
    img = Image.open(file.file)

    _, faces = face_detector.detect(img)

    recognized_students = []

    if faces is not None:
        embeddings = embedding_generator.generate(faces)
        if embeddings is not None:
            for embedding in embeddings:
                embedding = embedding.detach().cpu()
                recognized_student_id, max_similarity = matcher.match(embedding)

                if recognized_student_id and max_similarity > 0.8:
                    recognized_students.append(recognized_student_id)

    if recognized_students:
        try:
            # Assuming backend service is running on http://backend-service:8000
            response = requests.post(
                "http://backend-service:8000/recognize-result",
                json={"session_id": session_id, "recognized_students": recognized_students}
            )
            response.raise_for_status()  # Raise an exception for bad status codes
        except requests.exceptions.RequestException as e:
            print(f"Error sending recognition results to backend: {e}")
            return {"message": "Recognition complete, but failed to send results to backend.", "recognized_students": recognized_students}

    return {"recognized_students": recognized_students}
