"""Integration tests for the public API."""
import asyncio
import io
import pytest
import httpx
from typing import AsyncGenerator

pytestmark = pytest.mark.asyncio

# Test configuration
API_URL = "http://localhost:8000"
TIMEOUT = 30.0


@pytest.fixture
async def client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create an async HTTP client for testing."""
    async with httpx.AsyncClient(base_url=API_URL, timeout=TIMEOUT) as c:
        yield c


@pytest.fixture
async def wait_for_api():
    """Wait for API to be healthy before running tests."""
    max_retries = 30
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(base_url=API_URL, timeout=5.0) as client:
                response = await client.get("/health")
                if response.status_code == 200:
                    return
        except (httpx.ConnectError, httpx.TimeoutException):
            if attempt < max_retries - 1:
                await asyncio.sleep(1)
    raise RuntimeError(f"API did not become healthy after {max_retries} retries")


@pytest.mark.asyncio
async def test_health_check(client: httpx.AsyncClient, wait_for_api):
    """Test that the health check endpoint is working."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "public_api"


@pytest.mark.asyncio
async def test_create_document(client: httpx.AsyncClient, wait_for_api):
    """Test creating a document."""
    # Create a simple text file
    file_content = b"This is a test document with some content for testing purposes."
    files = {"file": ("test_document.txt", io.BytesIO(file_content), "text/plain")}

    response = await client.post("/v1/documents", files=files)

    assert response.status_code == 202, f"Expected 202, got {response.status_code}: {response.text}"
    data = response.json()
    
    assert "id" in data
    assert data["filename"] == "test_document.txt"
    assert data["content_type"] == "text/plain"
    assert data["size"] == len(file_content)
    assert "created_at" in data
    
    return data["id"]


@pytest.mark.asyncio
async def test_list_documents(client: httpx.AsyncClient, wait_for_api):
    """Test listing documents."""
    # First, create a document
    file_content = b"Document for listing test."
    files = {"file": ("list_test.txt", io.BytesIO(file_content), "text/plain")}
    create_response = await client.post("/v1/documents", files=files)
    assert create_response.status_code == 202
    created_doc_id = create_response.json()["id"]

    # List documents
    response = await client.get("/v1/documents", params={"skip": 0, "limit": 10})

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    
    assert "items" in data
    assert "total" in data
    assert "skip" in data
    assert "limit" in data
    assert "has_more" in data
    
    assert data["skip"] == 0
    assert data["limit"] == 10
    assert data["total"] >= 1
    assert any(doc["id"] == created_doc_id for doc in data["items"])


@pytest.mark.asyncio
async def test_get_document(client: httpx.AsyncClient, wait_for_api):
    """Test retrieving a specific document."""
    # Create a document
    file_content = b"Get document test content."
    files = {"file": ("get_test.txt", io.BytesIO(file_content), "text/plain")}
    create_response = await client.post("/v1/documents", files=files)
    assert create_response.status_code == 202
    doc_id = create_response.json()["id"]

    # Get the document
    response = await client.get(f"/v1/documents/{doc_id}")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    
    assert data["id"] == doc_id
    assert data["filename"] == "get_test.txt"
    assert data["content_type"] == "text/plain"
    assert data["size"] == len(file_content)


@pytest.mark.asyncio
async def test_query(client: httpx.AsyncClient, wait_for_api):
    """Test querying documents."""
    # Create a document first
    file_content = b"This document contains important information about machine learning and AI systems."
    files = {"file": ("query_test.txt", io.BytesIO(file_content), "text/plain")}
    create_response = await client.post("/v1/documents", files=files)
    assert create_response.status_code == 202
    
    # Wait a bit for async processing to start (optional, depends on your system)
    await asyncio.sleep(2)

    # Query the documents
    query_payload = {
        "query": "machine learning information",
        "top_k": 5
    }
    response = await client.post("/v1/query", json=query_payload)

    # Query might return 0 results if retrieval service isn't fully initialized
    # or if chunks haven't been created yet, but it should succeed
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    
    assert "results" in data
    assert isinstance(data["results"], list)
    # Results might be empty if processing hasn't completed
    for result in data["results"]:
        assert "id" in result
        assert "document_id" in result
        assert "content" in result
        assert "chunk_index" in result
        assert "score" in result


@pytest.mark.asyncio
async def test_query_empty_raises_validation_error(client: httpx.AsyncClient, wait_for_api):
    """Test that empty queries are rejected."""
    query_payload = {
        "query": "",
        "top_k": 5
    }
    response = await client.post("/v1/query", json=query_payload)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_query_invalid_top_k_raises_validation_error(client: httpx.AsyncClient, wait_for_api):
    """Test that invalid top_k values are rejected."""
    query_payload = {
        "query": "test",
        "top_k": 150  # > 100
    }
    response = await client.post("/v1/query", json=query_payload)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_documents_pagination(client: httpx.AsyncClient, wait_for_api):
    """Test pagination in list documents."""
    # Create multiple documents
    for i in range(5):
        file_content = f"Test document {i}".encode()
        files = {"file": (f"doc_{i}.txt", io.BytesIO(file_content), "text/plain")}
        response = await client.post("/v1/documents", files=files)
        assert response.status_code == 202

    # Test with limit=2
    response = await client.get("/v1/documents", params={"skip": 0, "limit": 2})
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) <= 2
    assert data["limit"] == 2

    # Test with skip
    response = await client.get("/v1/documents", params={"skip": 2, "limit": 2})
    assert response.status_code == 200
    data = response.json()
    assert data["skip"] == 2


@pytest.mark.asyncio
async def test_get_nonexistent_document(client: httpx.AsyncClient, wait_for_api):
    """Test that getting a nonexistent document returns 404."""
    response = await client.get("/v1/documents/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_document_idempotency(client: httpx.AsyncClient, wait_for_api):
    """Test idempotent document creation."""
    file_content = b"Idempotency test content."
    files = {"file": ("idempotent_test.txt", io.BytesIO(file_content), "text/plain")}
    idempotency_key = "test-idempotency-key-12345"

    # Create document with idempotency key
    response1 = await client.post(
        "/v1/documents",
        files=files,
        headers={"Idempotency-Key": idempotency_key}
    )
    assert response1.status_code == 202
    doc1 = response1.json()

    # Create again with same idempotency key
    files = {"file": ("different_name.txt", io.BytesIO(file_content), "text/plain")}
    response2 = await client.post(
        "/v1/documents",
        files=files,
        headers={"Idempotency-Key": idempotency_key}
    )
    assert response2.status_code == 202
    doc2 = response2.json()

    # Should return the same document
    assert doc1["id"] == doc2["id"]
