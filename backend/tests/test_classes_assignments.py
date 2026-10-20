import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_create_class_unauthorized(client):
    response = client.post("/api/v1/classes", json={"name": "Test Class"})
    assert response.status_code == 403

def test_create_class_authorized(client):
    headers = {"X-Teacher-Code": settings.teacher_access_code}
    response = client.post("/api/v1/classes", json={"name": "Test Class"}, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Class"
    assert "share_code" in data
    assert len(data["share_code"]) == 6

def test_create_assignment_with_files(client, tmp_path):
    # 1. Create class
    headers = {"X-Teacher-Code": settings.teacher_access_code}
    res = client.post("/api/v1/classes", json={"name": "Upload Class"}, headers=headers)
    class_id = res.json()["id"]

    # 2. Create assignment with files
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(b"dummy pdf content")
    audio_path = tmp_path / "test.mp3"
    audio_path.write_bytes(b"dummy audio content")

    with open(pdf_path, "rb") as f_pdf, open(audio_path, "rb") as f_audio:
        res2 = client.post(
            "/api/v1/assignments",
            headers=headers,
            data={
                "class_id": class_id,
                "skill": "reading",
                "title": "Test Reading"
            },
            files={
                "content_file": ("test.pdf", f_pdf, "application/pdf"),
                "audio_file": ("test.mp3", f_audio, "audio/mpeg")
            }
        )
    assert res2.status_code == 200
    data = res2.json()
    assert data["title"] == "Test Reading"
    assert "content_file_url" in data
    assert "audio_url" in data
    assert data["id"] in data["content_file_url"]
    assert data["id"] in data["audio_url"]
