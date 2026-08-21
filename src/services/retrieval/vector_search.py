from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Chunk
from src.services.ingestion import embedding


async def search(session: AsyncSession, query: str, top_k: int = 20) -> list[dict]:
    """Search for top-k chunks matching the query using vector similarity."""
    query_vector = embedding.embed_text(query)
    stmt = (
        select(Chunk)
        .order_by(Chunk.embedding.cosine_distance(query_vector))
        .limit(top_k)
    )
    result = await session.execute(stmt)
    chunks = result.scalars().all()
    return [
        {"text": c.content, "document_id": c.document_id, "score": 1.0}
        for c in chunks
    ]
