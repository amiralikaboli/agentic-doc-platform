import grpc

from src.core.config import settings
from src.generated.retrieval.v1 import retrieval_pb2, retrieval_pb2_grpc


class RetrievalClient:
    def __init__(self):
        self.channel = grpc.insecure_channel(settings.GRPC_SERVER_ADDRESS)
        self.stub = retrieval_pb2_grpc.RetrievalStub(self.channel)

    def search(self, query: str, top_k: int = 5):
        req = retrieval_pb2.SearchRequest(query=query, top_k=top_k)
        return self.stub.Search(req)

    def close(self):
        self.channel.close()
