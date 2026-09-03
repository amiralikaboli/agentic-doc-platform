import logging

import grpc

from src.core.db import SessionLocal
from src.generated.retrieval.v1 import retrieval_pb2_grpc, retrieval_pb2
from src.services.retrieval.reranker import RerankerService
from src.services.retrieval.vector_search import search_candidates

logger = logging.getLogger(__name__)


class RetrievalServicer(retrieval_pb2_grpc.RetrievalServicer):
    def Search(self, request: retrieval_pb2.SearchRequest, context) -> retrieval_pb2.SearchResponse:
        db = SessionLocal()
        try:
            logger.info(f"Search query: '{request.query}' (top_k={request.top_k})")

            # Vector search: retrieve 2x top_k candidates
            candidate_chunks = search_candidates(session=db, query=request.query, top_k=2 * request.top_k)
            logger.info(f"Retrieved {len(candidate_chunks)} candidates from vector search")

            # Rerank
            reranker = RerankerService()
            ranked_chunks = reranker.rerank(query=request.query, candidates=candidate_chunks, top_k=request.top_k)
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
            context.abort(grpc.StatusCode.INTERNAL, "Internal error during search")
        finally:
            db.close()
