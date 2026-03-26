import os

EMBEDDINGS_FILE = os.getenv("EMBEDDINGS_FILE", "app/data/embeddings.json")
MATCH_THRESHOLD = float(os.getenv("MATCH_THRESHOLD", "0.60"))
DEVICE = os.getenv("TORCH_DEVICE", "cuda")
BACKEND_SERVICE_URL = os.getenv("BACKEND_SERVICE_URL", "http://backend-service:8000")
FORWARD_ATTENDANCE = os.getenv("FORWARD_ATTENDANCE", "false").lower() == "true"

# Database configuration for embedding storage
DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "smart_classroom")
