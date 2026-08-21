"""gRPC retrieval service application."""
import logging
from concurrent import futures

import grpc

from src.apps.retrieval_service import RetrievalServicer
from src.core.config import settings
from src.core.models import get_model_manager
from src.generated.retrieval.v1 import retrieval_pb2_grpc

logger = logging.getLogger(__name__)


def serve():
    logger.info("🚀 gRPC Retrieval Service starting...")

    # Cold-start: Initialize models needed for retrieval service (embedder only)
    try:
        model_manager = get_model_manager()
        model_manager.initialize_for_retrieval()
        logger.info("✓ Models initialized and ready")
    except Exception as e:
        logger.error(f"✗ Failed to initialize models: {e}")
        raise

    # Create gRPC server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=settings.GRPC_MAX_WORKERS))
    retrieval_pb2_grpc.add_RetrievalServicer_to_server(RetrievalServicer(), server)
    server.add_insecure_port(f"[::]:{settings.GRPC_PORT}")

    server.start()
    logger.info(f"✓ gRPC server listening on port {settings.GRPC_PORT}")
    logger.info("✓ Retrieval Service ready")

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down gRPC server...")
        server.stop(grace=5)
        logger.info("✓ Server shut down gracefully")


if __name__ == "__main__":
    serve()
