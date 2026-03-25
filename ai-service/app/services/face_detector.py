from facenet_pytorch import MTCNN
import torch
from PIL import Image

class FaceDetector:
    def __init__(self):
        self.device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
        self.mtcnn = MTCNN(keep_all=True, device=self.device)

    def detect(self, img: Image.Image):
        boxes, _ = self.mtcnn.detect(img)
        return boxes, self.mtcnn(img, save_path=None)
