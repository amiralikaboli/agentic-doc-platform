from typing import List

from langchain_huggingface import HuggingFaceEmbeddings

from src.models import ChunkResult

embedder = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    encode_kwargs={"normalize_embeddings": True}
)

chunker = None
reranker = None


def rerank(query: str, candidates: List[ChunkResult], top_k: int) -> List[ChunkResult]:
    pairs = [[query, chunk.content] for chunk in candidates]
    scores = reranker.predict(pairs)
    for chunk, score in zip(candidates, scores):
        chunk.score = score
    return sorted(candidates, key=lambda x: x.score, reverse=True)[:top_k]
