from unittest.mock import patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_async_ingestion_status_polling(async_client: AsyncClient):
    """BB2 DoD: Uploading returns 'pending', polling transitions to 'done' or 'failed'."""
    files = {"file": ("test.txt", b"Content", "text/plain")}

    # Mock the Celery delay call to prevent actual background execution in API test
    with patch("src.tasks.process_document_task.delay") as mock_task:
        mock_task.return_value.id = "mock-task-id"

        # 1. Upload Document
        upload_resp = await async_client.post("/v1/documents", files=files)
        assert upload_resp.status_code == 202
        doc_id = upload_resp.json()["id"]

        # 2. Check Status (Pending)
        with patch("src.api.documents.get_task_status", return_value="pending"):
            status_resp = await async_client.get(f"/v1/documents/{doc_id}/status")
            assert status_resp.status_code == 200
            assert status_resp.json()["status"] == "pending"

        # 3. Check Status (Done)
        with patch("src.api.documents.get_task_status", return_value="done"):
            status_resp_done = await async_client.get(f"/v1/documents/{doc_id}/status")
            assert status_resp_done.json()["status"] == "done"