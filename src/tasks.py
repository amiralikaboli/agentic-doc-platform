import time

from src.celery_app import celery_app


@celery_app.task
def dummy_task(doc_id: str):
    dest_path = f"data/{doc_id}"
    with open(dest_path, "rb") as f:
        content = f.read()
    if len(content) == 0:
        raise ValueError("File is empty or corrupt")
    time.sleep(5)