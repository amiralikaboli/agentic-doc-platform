from typing import List

from src.db import ChunkModel

embedder = None
chunker = None
reranker = None


def load_embedder():
    global embedder
    if embedder is None:
        from langchain_huggingface import HuggingFaceEmbeddings
        embedder = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            encode_kwargs={"normalize_embeddings": True},
        )
    return embedder


def load_chunker():
    global chunker
    if chunker is None:
        from langchain_experimental.text_splitter import SemanticChunker
        chunker = SemanticChunker(embeddings=load_embedder())
    return chunker


def load_reranker():
    global reranker
    if reranker is None:
        from sentence_transformers import CrossEncoder
        reranker = CrossEncoder('BAAI/bge-reranker-base')
    return reranker


def rerank(query: str, candidates: List[ChunkModel], top_k: int):
    pairs = [[query, chunk.content] for chunk in candidates]
    scores = reranker.predict(pairs)
    return sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)[:top_k]
