from typing import List
from PIL import Image
import torch

from .face_detector import FaceDetector
from .embedding_generator import EmbeddingGenerator

class RegistrationService:
    def __init__(self, embeddings_storage, face_detector: FaceDetector, embedding_generator: EmbeddingGenerator):
        self.embeddings_storage = embeddings_storage
        self.face_detector = face_detector
        self.embedding_generator = embedding_generator

    def register_student(self, student_id: str, files: List):
        embeddings = []
        for file in files:
            img = Image.open(file)
            _, faces = self.face_detector.detect(img)
            
            if faces is not None:
                embedding = self.embedding_generator.generate(faces)
                if embedding is not None:
                    embeddings.append(embedding.detach().cpu())

        if embeddings:
            avg_embedding = torch.mean(torch.stack(embeddings), dim=0)
            self.embeddings_storage[student_id] = avg_embedding
            return True
        
        return False

