import src.embedding  # access embedder/chunker as module attributes — set once at worker startup
from src.celery_app import celery_app
from src.db import SessionLocal, ChunkModel


@celery_app.task
def process_document_task(doc_id: str):
    dest_path = f"data/{doc_id}"
    with open(dest_path, "r", encoding="utf-8") as f:
        content = f.read()

    chunks = src.embedding.chunker.split_text(content)
    if not chunks:
        raise ValueError(f"No text chunks could be extracted from document {doc_id}")

    chunk_embeds = src.embedding.embedder.embed_documents(chunks)

    db = SessionLocal()
    try:
        for idx, (text, embed) in enumerate(zip(chunks, chunk_embeds)):
            db.add(
                ChunkModel(
                    document_id=doc_id,
                    content=text,
                    chunk_index=idx,
                    embedding=embed
                )
            )
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
