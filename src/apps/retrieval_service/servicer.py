import logging

import grpc

from src.core.db import SessionLocal
from src.db.models import Chunk
from src.generated.retrieval.v1 import retrieval_pb2_grpc, retrieval_pb2
from src.services.ingestion.embedding import EmbeddingService
from src.services.retrieval.reranker import RerankerService

logger = logging.getLogger(__name__)


class RetrievalServicer(retrieval_pb2_grpc.RetrievalServicer):
    def Search(self, request: retrieval_pb2.SearchRequest, context) -> retrieval_pb2.SearchResponse:
        db = SessionLocal()
        try:
            logger.info(f"Search query: '{request.query}' (top_k={request.top_k})")

            # Initialize services (use pre-loaded models from ModelManager)
            embedder = EmbeddingService()
            reranker = RerankerService()

            # Embed query
            query_vector = embedder.embed(request.query)
            logger.debug("Query embedded")

            # Vector search: retrieve 2x top_k candidates
            dist_col = Chunk.embedding.cosine_distance(query_vector).label("distance")
            query = db.query(Chunk, dist_col)
            results = query.order_by(dist_col).limit(2 * request.top_k).all()
            chunk_results = [chunk for chunk, _ in results]
            logger.info(f"Retrieved {len(chunk_results)} candidates from vector search")

            # Rerank
            ranked_chunks = reranker.rerank(query=request.query, candidates=chunk_results, top_k=request.top_k)
            logger.info(f"Reranked to top {len(ranked_chunks)} results")

            return retrieval_pb2.SearchResponse(
                results=[
                    retrieval_pb2.RetrievedChunk(
                        id=str(chunk.id),
                        document_id=str(chunk.document_id),
                        content=chunk.content,
                        chunk_index=chunk.chunk_index,
                        score=float(score),
                    )
                    for chunk, score in ranked_chunks
                ]
            )
        except Exception as e:
            logger.error(f"Search failed: {e}", exc_info=True)
            context.abort(grpc.StatusCode.INTERNAL, str(e))
        finally:
            db.close()
