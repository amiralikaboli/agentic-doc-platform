import uuid

import pytest
from fastapi.testclient import TestClient

from src.api import app, id2document, idempotency_store


@pytest.fixture(autouse=True)
def clean_store(monkeypatch, tmp_path):
    """Keep each test isolated and make uploaded files disposable."""
    id2document.clear()
    idempotency_store.clear()

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.chdir(tmp_path)

    yield

    id2document.clear()
    idempotency_store.clear()


@pytest.fixture
def client():
    return TestClient(app)


def upload(client, filename="example.txt", content=b"hello world", content_type="text/plain", key=None):
    headers = {"Idempotency-Key": key} if key else {}
    return client.post(
        "/v1/documents",
        files={"file": (filename, content, content_type)},
        headers=headers,
    )


def test_create_document_returns_202_and_document_metadata(client):
    response = upload(client)

    assert response.status_code == 202
    body = response.json()

    assert uuid.UUID(body["id"])
    assert body["status"] == "uploaded"
    assert response.headers["Location"] == f"/v1/documents/{body['id']}"


def test_get_document_returns_created_document(client):
    created = upload(client).json()

    response = client.get(f"/v1/documents/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_get_unknown_document_returns_consistent_error_schema(client):
    missing_id = uuid.uuid4()

    response = client.get(f"/v1/documents/{missing_id}")

    assert response.status_code == 404


def test_list_documents_uses_offset_pagination(client):
    for i in range(3):
        upload(client, filename=f"file-{i}.txt", content=f"file-{i}".encode())

    response = client.get("/v1/documents", params={"skip": 1, "limit": 1})

    assert response.status_code == 200
    body = response.json()

    assert body["total"] == 3
    assert body["skip"] == 1
    assert body["limit"] == 1
    assert body["has_more"] is True
    assert len(body["items"]) == 1
    assert body["items"][0]["filename"] == "file-1.txt"


def test_same_idempotency_key_does_not_create_duplicate(client):
    key = "create-document-123"

    first = upload(client, filename="first.txt", content=b"same request", key=key)
    second = upload(client, filename="first.txt", content=b"same request", key=key)

    assert first.status_code == 202
    assert second.status_code == 202

    first_body = first.json()
    second_body = second.json()

    assert second_body["id"] == first_body["id"]
    assert len(id2document) == 1


def test_missing_upload_file_returns_consistent_error_schema(client):
    response = client.post("/v1/documents")

    assert response.status_code == 422


def test_invalid_document_id_returns_consistent_error_schema(client):
    response = client.get("/v1/documents/not-a-uuid")

    assert response.status_code == 422
