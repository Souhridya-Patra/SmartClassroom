import os

EMBEDDINGS_FILE = os.getenv("EMBEDDINGS_FILE", "app/data/embeddings.json")
MATCH_THRESHOLD = float(os.getenv("MATCH_THRESHOLD", "0.60"))
DEVICE = os.getenv("TORCH_DEVICE", "cuda")
BACKEND_SERVICE_URL = os.getenv("BACKEND_SERVICE_URL", "http://backend-service:8000")
FORWARD_ATTENDANCE = os.getenv("FORWARD_ATTENDANCE", "false").lower() == "true"
