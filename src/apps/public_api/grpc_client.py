import grpc

from src.core.config import settings
from src.generated.retrieval.v1 import retrieval_pb2, retrieval_pb2_grpc


class RetrievalClient:
    _instance = None
    channel: grpc.Channel | None = None
    stub: retrieval_pb2_grpc.RetrievalStub | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def init(cls):
        if cls.channel:
            return
        cls.channel = grpc.insecure_channel(settings.GRPC_SERVER_ADDRESS)
        cls.stub = retrieval_pb2_grpc.RetrievalStub(cls.channel)

    @classmethod
    def search(cls, query: str, top_k: int = 5):
        if cls.stub is None:
            raise RuntimeError("RetrievalClient not initialized. Call init() first.")
        req = retrieval_pb2.SearchRequest(query=query, top_k=top_k)
        return cls.stub.Search(req, timeout=settings.GRPC_REQUEST_TIMEOUT)

    @classmethod
    def close(cls):
        if cls.channel is not None:
            cls.channel.close()
            cls.channel = None
            cls.stub = None


def get_retrieval_client():
    return RetrievalClient()
