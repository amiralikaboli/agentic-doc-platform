from sqlalchemy.orm import Session

from src.db.models import Chunk
from src.services.ingestion.embedding import EmbeddingService


def search_candidates(session: Session, query: str, top_k: int = 20) -> list[Chunk]:
    """Search for top-k chunks matching the query using vector similarity."""

    # Embed query
    embedder = EmbeddingService()
    query_vector = embedder.embed(query)

    # Vector search: retrieve 2x top_k candidates
    dist_col = Chunk.embedding.cosine_distance(query_vector).label("distance")
    query = session.query(Chunk, dist_col)
    results = query.order_by(dist_col).limit(top_k).all()
    return [chunk for chunk, _ in results]
