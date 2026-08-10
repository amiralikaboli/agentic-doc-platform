from typing import Dict, Optional

from fastapi import FastAPI

from src.db import init_db

app = FastAPI()


@app.on_event("startup")
def startup_event():
    init_db()


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
