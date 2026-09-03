import re

import numpy as np

from src.services.ingestion.embedding import EmbeddingService


class ChunkingService:
    def __init__(self):
        self.embedding_service = EmbeddingService()

    def split_text(self, text: str) -> list[str]:
        sentences = [s for s in re.split(r"(?<=[.?!])\s+", text) if s]
        if len(sentences) == 1:
            return sentences

        embeddings = self.embedding_service.embed(sentences)

        distances = []
        for i in range(len(embeddings) - 1):
            a, b = embeddings[i], embeddings[i + 1]
            sim = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
            distances.append(1 - sim)

        threshold = np.percentile(distances, 95.0)
        breakpoints = [i for i, d in enumerate(distances) if d > threshold]

        # TODO: add a cap for number of sentences/tokens in each chunk
        chunks, start = [], 0
        for bp in breakpoints:
            chunks.append(" ".join(sentences[start: bp + 1]))
            start = bp + 1
        chunks.append(" ".join(sentences[start:]))

        return chunks
