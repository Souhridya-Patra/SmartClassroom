from __future__ import annotations

import numpy as np
import torch
from facenet_pytorch import InceptionResnetV1, MTCNN
from PIL import Image


class FaceEngine:
    def __init__(self, device_name: str):
        if device_name == "cuda" and not torch.cuda.is_available():
            device_name = "cpu"
        self.device = torch.device(device_name)
        self.detector = MTCNN(keep_all=True, device=self.device)
        self.encoder = InceptionResnetV1(pretrained="vggface2").eval().to(self.device)

    def detect_faces(self, bgr_image: np.ndarray) -> torch.Tensor | None:
        rgb = bgr_image[:, :, ::-1]
        pil_image = Image.fromarray(rgb)
        faces = self.detector(pil_image)
        if faces is None:
            return None

        if faces.ndim == 3:
            faces = faces.unsqueeze(0)
        return faces

    def embedding(self, face_tensor: torch.Tensor) -> np.ndarray:
        with torch.no_grad():
            tensor = face_tensor.unsqueeze(0).to(self.device)
            vector = self.encoder(tensor).squeeze(0).detach().cpu().numpy().astype(np.float32)

        norm = float(np.linalg.norm(vector))
        if norm > 0:
            vector = vector / norm
        return vector

    def embeddings(self, face_tensors: torch.Tensor) -> np.ndarray:
        with torch.no_grad():
            batch = face_tensors.to(self.device)
            vectors = self.encoder(batch).detach().cpu().numpy().astype(np.float32)

        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return vectors / norms

    @staticmethod
    def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))
