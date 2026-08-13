import os
from contextlib import asynccontextmanager
from typing import Dict, Optional

from fastapi import FastAPI

GRPC_RETRIEVAL_URL = os.getenv("GRPC_RETRIEVAL_URL", "localhost:50051")


@asynccontextmanager
async def lifespan(app: FastAPI):
    from src.db import init_db
    init_db()

    import grpc
    from src.api.protos import retrieval_pb2_grpc
    channel = grpc.insecure_channel(GRPC_RETRIEVAL_URL)
    app.state.grpc_channel = channel
    app.state.grpc_stub = retrieval_pb2_grpc.RetrievalStub(channel)

    yield  # app runs here

    channel.close()


app = FastAPI(lifespan=lifespan)


class APIError(Exception):
    def __init__(self, status_code: int, message: str, details: Optional[Dict] = None):
        self.status_code = status_code
        self.message = message
        self.details = details if details else {}


@app.get("/")
def root():
    return "Welcome!"


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


from src.api import documents, query
