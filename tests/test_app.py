import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "/docs" in response.text


def test_get_templates(client):
    response = client.get("/templates")
    assert response.status_code == 200
    templates = response.json()
    assert isinstance(templates, list)
    assert "certificate" in templates
    assert "table" in templates


def test_compile_minimal_template(client):
    response = client.post(
        "/templates/minimal/compile",
        json={"jsonInputs": [], "blobInputs": []},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"


def test_create_certificate(client):
    response = client.post(
        "/certificates",
        json={"name": "Test User"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"


def test_upload_blob(client):
    response = client.post(
        "/blobs",
        files={"file": ("test.txt", b"test content", "text/plain")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
