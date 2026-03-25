import cv2
import numpy as np


def decode_image_bytes(raw: bytes) -> np.ndarray:
    data = np.frombuffer(raw, dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Invalid image payload")
    return image
