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
        self.threshold = 0.9

    def detect_faces(self, bgr_image: np.ndarray) -> torch.Tensor | None:
        faces, _, _ = self.detect_faces_with_boxes(bgr_image)
        return faces

    def detect_faces_with_boxes(self, bgr_image: np.ndarray) -> tuple[torch.Tensor | None, np.ndarray | None, np.ndarray | None]:
        rgb = bgr_image[:, :, ::-1]
        pil_image = Image.fromarray(rgb)

        boxes, probabilities, landmarks = self.detector.detect(pil_image, landmarks=True)
        if boxes is None or len(boxes) == 0:
            return None, None, None

        valid_indices = [i for i, prob in enumerate(probabilities) if prob is not None and prob >= self.threshold]
        
        if not valid_indices:
            return None, None, None
        
        boxes = boxes[valid_indices]
        if landmarks is not None:
            landmarks = landmarks[valid_indices]

        faces = self.detector.extract(pil_image, boxes, save_path=None)
        if faces is None:
            return None, None, None

        if isinstance(faces, list):
            valid_faces = [face for face in faces if face is not None]
            if not valid_faces:
                return None, None, None
            faces = torch.stack(valid_faces)

        if faces.ndim == 3:
            faces = faces.unsqueeze(0)

        count = min(faces.shape[0], len(boxes))
        if count == 0:
            return None, None, None

        result_landmarks = None
        if landmarks is not None:
            result_landmarks = landmarks[:count].astype(np.float32)

        return faces[:count], boxes[:count].astype(np.float32), result_landmarks

    def embedding(self, face_tensor: torch.Tensor) -> np.ndarray:
        with torch.no_grad():
            if face_tensor.ndim == 3:
                tensor = face_tensor.unsqueeze(0).to(self.device)
            elif face_tensor.ndim == 4:
                tensor = face_tensor.to(self.device)
            else:
                raise ValueError(f"Unexpected tensor shape: {face_tensor.shape}. Expected a 3D or 4D tensor.")
            
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
