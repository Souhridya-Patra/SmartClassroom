import torch

class Matcher:
    def __init__(self, embeddings_storage):
        self.embeddings_storage = embeddings_storage

    def match(self, embedding):
        max_similarity = 0
        recognized_student_id = None
        
        for student_id, student_embedding in self.embeddings_storage.items():
            similarity = self.cosine_similarity(embedding, student_embedding)
            if similarity > max_similarity:
                max_similarity = similarity
                recognized_student_id = student_id
        
        return recognized_student_id, max_similarity

    def cosine_similarity(self, embedding1, embedding2):
        return torch.nn.functional.cosine_similarity(embedding1, embedding2, dim=0).item()
