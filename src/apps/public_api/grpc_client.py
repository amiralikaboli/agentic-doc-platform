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

    def init(self):
        if self.channel:
            return
        self.channel = grpc.insecure_channel(settings.GRPC_SERVER_ADDRESS)
        self.stub = retrieval_pb2_grpc.RetrievalStub(self.channel)

    def search(self, query: str, top_k: int = 5):
        if self.stub is None:
            raise RuntimeError("RetrievalClient not initialized. Call init() first.")
        req = retrieval_pb2.SearchRequest(query=query, top_k=top_k)
        return self.stub.Search(req, timeout=settings.GRPC_REQUEST_TIMEOUT)

    def close(self):
        if self.channel is not None:
            self.channel.close()
            self.channel = None
            self.stub = None


def get_retrieval_client():
    return RetrievalClient()
