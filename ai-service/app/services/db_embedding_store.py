import json
import os
from typing import Dict, List

import mysql.connector
import numpy as np


class DBEmbeddingStore:
    """Database-backed embedding store with optional JSON fallback."""

    def __init__(
        self,
        db_host: str = "host.docker.internal",
        db_port: int = 3306,
        db_user: str = "root",
        db_password: str = "",
        db_name: str = "smart_classroom",
        json_fallback: str | None = None,
    ):
        self.db_host = db_host
        self.db_port = db_port
        self.db_user = db_user
        self.db_password = db_password
        self.db_name = db_name
        self.json_fallback = json_fallback
        self._cache: Dict[str, List[float]] | None = None

    def _get_connection(self):
        return mysql.connector.connect(
            host=self.db_host,
            port=self.db_port,
            user=self.db_user,
            password=self.db_password,
            database=self.db_name,
        )

    def _refresh_cache(self) -> None:
        """Load all embeddings into memory cache."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT student_id, embedding, samples_count
                FROM facial_embeddings
                ORDER BY created_at DESC
                """
            )
            rows = cursor.fetchall()
            cursor.close()
            conn.close()

            self._cache = {}
            for row in rows:
                if student_id := row["student_id"]:
                    embedding_json = row["embedding"]
                    if isinstance(embedding_json, str):
                        embedding_json = json.loads(embedding_json)
                    self._cache[student_id] = embedding_json

        except Exception as exc:
            print(f"Warning: Could not load embeddings from database: {exc}")
            if self.json_fallback:
                self._cache = self._load_fallback()
            else:
                self._cache = {}

    def _load_fallback(self) -> Dict[str, List[float]]:
        """Load embeddings from JSON fallback file if available."""
        if not self.json_fallback or not os.path.exists(self.json_fallback):
            return {}
        try:
            with open(self.json_fallback, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {sid: row.get("embedding", []) for sid, row in data.items()}
        except Exception:
            return {}

    def student_count(self) -> int:
        """Get number of registered students."""
        if self._cache is None:
            self._refresh_cache()
        return len(self._cache or {})

    def get_samples(self, student_id: str) -> int:
        """Get sample count for a student."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT MAX(samples_count) FROM facial_embeddings WHERE student_id = %s",
                (student_id,),
            )
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            return int(result[0]) if result and result[0] else 0
        except Exception:
            return 0

    def register(self, student_id: str, embedding: np.ndarray) -> int:
        """Register or update a student embedding. Returns total sample count."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("SELECT id FROM students WHERE id = %s", (student_id,))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO students (id) VALUES (%s)", (student_id,))
                conn.commit()

            cursor.execute(
                "SELECT embedding, samples_count FROM facial_embeddings WHERE student_id = %s ORDER BY created_at DESC LIMIT 1",
                (student_id,),
            )
            row = cursor.fetchone()

            if row:
                old_embedding_json = row["embedding"]
                if isinstance(old_embedding_json, str):
                    old_embedding_json = json.loads(old_embedding_json)
                old_embedding = np.array(old_embedding_json, dtype=np.float32)
                old_samples = row["samples_count"]

                merged = (old_embedding * old_samples + embedding) / (old_samples + 1)
                norm = float(np.linalg.norm(merged))
                if norm > 0:
                    merged = merged / norm

                new_samples = old_samples + 1
                cursor.execute(
                    "INSERT INTO facial_embeddings (student_id, embedding, samples_count) VALUES (%s, %s, %s)",
                    (student_id, json.dumps(merged.tolist()), new_samples),
                )
            else:
                new_samples = 1
                cursor.execute(
                    "INSERT INTO facial_embeddings (student_id, embedding, samples_count) VALUES (%s, %s, %s)",
                    (student_id, json.dumps(embedding.tolist()), new_samples),
                )

            conn.commit()
            cursor.close()
            conn.close()

            self._cache = None
            return new_samples

        except Exception as exc:
            print(f"Warning: Could not register embedding to database: {exc}")
            return 0

    def get_all(self) -> Dict[str, List[float]]:
        """Get all registered embeddings."""
        if self._cache is None:
            self._refresh_cache()
        return self._cache or {}
