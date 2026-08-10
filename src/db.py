import os
import uuid
from typing import List, Tuple

from pgvector.sqlalchemy import Vector
from sqlalchemy import create_engine, Column, UUID, Text, text, Integer
from sqlalchemy.orm import sessionmaker, declarative_base, Session

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgrespassword@postgres:5432/app_db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class ChunkModel(Base):
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), nullable=False)
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    embedding = Column(Vector(384))


def init_db():
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()

    Base.metadata.create_all(bind=engine)

    with engine.connect() as conn:
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_chunks_hnsw ON document_chunks USING hnsw (embedding vector_cosine_ops);"
        ))
        conn.commit()


def search_similar_chunks(db: Session, query_vector: List[float], top_k: int = 3) -> List[Tuple[ChunkModel, float]]:
    dist_col = ChunkModel.embedding.cosine_distance(query_vector).label("distance")
    query = db.query(ChunkModel, dist_col)
    results = query.order_by(dist_col).limit(top_k).all()
    return results
