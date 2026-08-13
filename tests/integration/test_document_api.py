import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_document_idempotency(async_client: AsyncClient):
    """BB1 DoD: Re-sending the same Idempotency-Key doesn't create a duplicate document."""
    headers = {"Idempotency-Key": "test-idemp-key-123"}
    files = {"file": ("test.pdf", b"Dummy PDF content", "application/pdf")}

    # First request
    response1 = await async_client.post("/v1/documents", headers=headers, files=files)
    assert response1.status_code == 202
    data1 = response1.json()
    assert "id" in data1

    # Second request with the same key
    files = {"file": ("test.pdf", b"Dummy PDF content", "application/pdf")}
    response2 = await async_client.post("/v1/documents", headers=headers, files=files)
    assert response2.status_code == 202
    data2 = response2.json()

    # Assert IDs match (idempotent response)
    assert data1["id"] == data2["id"]


@pytest.mark.asyncio
async def test_document_pagination(async_client: AsyncClient):
    """BB1 DoD: Test offset/cursor pagination on GET /v1/documents."""
    response = await async_client.get("/v1/documents?limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data.get("items"), list)
    assert "total" in data


@pytest.mark.asyncio
async def test_structured_error_taxonomy(async_client: AsyncClient):
    """BB1 DoD: Consistent error schema (code, message, details)."""
    response = await async_client.get("/v1/documents/invalid-uuid-format")
    assert response.status_code == 404
    error_data = response.json()
    assert "code" in error_data
    assert "message" in error_data
    assert error_data["code"] == "DOCUMENT_NOT_FOUND"
