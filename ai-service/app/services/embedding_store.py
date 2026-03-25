import json
import os
from typing import Dict, List

import numpy as np


class EmbeddingStore:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._data = self._load()

    def _load(self) -> Dict[str, dict]:
        if not os.path.exists(self.file_path):
            return {}
        with open(self.file_path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        with open(self.file_path, "w", encoding="utf-8") as handle:
            json.dump(self._data, handle)

    def student_count(self) -> int:
        return len(self._data)

    def get_samples(self, student_id: str) -> int:
        record = self._data.get(student_id)
        if record is None:
            return 0
        return int(record.get("samples", 0))

    def register(self, student_id: str, embedding: np.ndarray) -> int:
        record = self._data.get(student_id)
        if record is None:
            self._data[student_id] = {
                "samples": 1,
                "embedding": embedding.tolist(),
            }
            self._save()
            return 1

        old_samples = int(record["samples"])
        old_embedding = np.array(record["embedding"], dtype=np.float32)
        merged = (old_embedding * old_samples + embedding) / (old_samples + 1)
        norm = float(np.linalg.norm(merged))
        if norm > 0:
            merged = merged / norm

        self._data[student_id] = {
            "samples": old_samples + 1,
            "embedding": merged.tolist(),
        }
        self._save()
        return old_samples + 1

    def get_all(self) -> Dict[str, List[float]]:
        return {student_id: row["embedding"] for student_id, row in self._data.items()}
