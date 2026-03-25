from facenet_pytorch import InceptionResnetV1
import torch

class EmbeddingGenerator:
    def __init__(self):
        self.device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
        self.resnet = InceptionResnetV1(pretrained='vggface2').eval().to(self.device)

    def generate(self, faces):
        if faces is None:
            return None
        return self.resnet(faces)
