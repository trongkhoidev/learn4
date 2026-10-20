import io
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app
from app.db.base import Base
from app.db.session import engine
from app.core.config import settings
from app.modules.speaking.assessment.engine import grade_speaking

Base.metadata.create_all(bind=engine)
client = TestClient(app)

def test_grade_speaking_mock():
    settings.stt_provider = "mock"
    settings.llm_provider = "mock"
    
    result = grade_speaking(audio_path="dummy.webm", question="Describe a topic", task_type="PART 2")
    
    assert "transcript" in result
    assert "overall" in result
    assert "pronun" in result
    assert "fluency" in result
    assert "grammar" in result
    assert "vocab" in result
    
    assert "score" in result["pronun"]
    assert "score" in result["fluency"]
    assert "features" in result["fluency"]
    assert "score" in result["grammar"]
    assert "errors" in result["grammar"]
    assert "score" in result["vocab"]
    
    assert "color_coded_transcript" in result
    assert len(result["color_coded_transcript"]) > 0

@patch("app.modules.speaking.common.compress_audio")
@patch("app.modules.speaking.common.blob_service.upload_bytes", return_value="http://fake.url/audio.webm")
def test_speaking_practice_endpoint(mock_upload, mock_compress):
    settings.stt_provider = "mock"
    settings.llm_provider = "mock"
    
    def fake_compress(in_path, out_path):
        with open(out_path, "wb") as f:
            f.write(b"fake compressed audio")
        return out_path
    
    mock_compress.side_effect = fake_compress
    
    audio_content = b"fake audio content"
    file = io.BytesIO(audio_content)
    file.name = "test.webm"
    
    response = client.post(
        "/api/v1/speaking/practice",
        data={
            "student_name": "Test Student",
            "question_text": "Describe your favorite book",
            "part_type": "PART 2"
        },
        files={"file": ("test.webm", file, "audio/webm")}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["student_name"] == "Test Student"
    assert "result" in data
    assert "overall" in data["result"]
