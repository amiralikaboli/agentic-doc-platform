import time
from concurrent import futures

import grpc

import src.embedding  # embedder/reranker set once in serve(), read here via module reference
from src.api.protos import retrieval_pb2_grpc, retrieval_pb2
from src.db import SessionLocal, ChunkModel


class RetrievalServicer(retrieval_pb2_grpc.RetrievalServicer):
    def Search(self, request: retrieval_pb2.SearchRequest, context) -> retrieval_pb2.SearchResponse:
        db = SessionLocal()
        try:
            start_time = time.perf_counter()

            query_vector = src.embedding.embedder.embed_query(request.query)
            dist_col = ChunkModel.embedding.cosine_distance(query_vector).label("distance")
            query = db.query(ChunkModel, dist_col)
            results = query.order_by(dist_col).limit(2 * request.top_k).all()
            chunk_results = [chunk for chunk, _ in results]
            ranked_chunks = src.embedding.rerank(query=request.query, candidates=chunk_results, top_k=request.top_k)

            elapsed_ms = (time.perf_counter() - start_time) * 1000
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
                ],
                search_time_ms=elapsed_ms,
            )
        except Exception as e:
            context.abort(grpc.StatusCode.INTERNAL, str(e))
        finally:
            db.close()


def serve():
    # Load once at cold start, not on first request.
    src.embedding.load_embedder()
    src.embedding.load_reranker()

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    retrieval_pb2_grpc.add_RetrievalServicer_to_server(RetrievalServicer(), server)
    server.add_insecure_port(f"[::]:50051")
    server.start()
    print(f"Retrieval gRPC server listening on :50051")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
