import io
import time
import uuid
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from app.modules.speaking.models import (
    PracticeSession, SpeakingAssessmentJob, SpeakingTurn,
)
from app.modules.speaking import jobs as queue
from app.integrations.storage.blob import blob_service


Base.metadata.create_all(bind=engine)


def test_local_audio_url_is_browser_accessible():
    key = f"tests/{uuid.uuid4()}.webm"
    url = blob_service.upload_bytes(key, b"browser-audio", "audio/webm")
    try:
        with TestClient(app) as client:
            response = client.get(url)
        assert response.status_code == 200
        assert response.content == b"browser-audio"
        assert response.headers["content-type"] == "video/webm"
    finally:
        blob_service.delete(key)


def _fake_compress(source, target):
    Path(target).write_bytes(b"encoded")
    return target


def test_async_practice_contract(monkeypatch):
    monkeypatch.setattr(settings, "stt_provider", "mock")
    with TestClient(app) as client, patch(
        "app.modules.speaking.common.compress_audio", side_effect=_fake_compress
    ), patch("app.modules.speaking.practice.jobs.enqueue_speaking"):
        response = client.post(
            "/api/v1/speaking/practice",
            data={
                "student_name": "Async Student",
                "question_text": "Tell me about your home",
                "part_type": "PART 1",
                "async_processing": "true",
            },
            files={"file": ("answer.webm", io.BytesIO(b"audio"), "audio/webm")},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "pending"
        fetched = client.get(f"/api/v1/speaking/practice/{payload['id']}")
        assert fetched.status_code == 200
        assert fetched.json()["status"] == "pending"


def test_async_practice_worker_end_to_end(monkeypatch):
    monkeypatch.setattr(settings, "stt_provider", "mock")
    monkeypatch.setattr(settings, "llm_provider", "mock")
    with TestClient(app) as client, patch(
        "app.modules.speaking.common.compress_audio", side_effect=_fake_compress
    ):
        response = client.post(
            "/api/v1/speaking/practice",
            data={
                "student_name": "Queue Student",
                "question_text": "Tell me about your home",
                "part_type": "PART 1",
                "async_processing": "true",
            },
            files={"file": ("answer.webm", io.BytesIO(b"audio"), "audio/webm")},
        )
        session_id = response.json()["id"]
        payload = response.json()
        deadline = time.time() + 5
        while payload["status"] == "pending" and time.time() < deadline:
            time.sleep(0.1)
            payload = client.get(f"/api/v1/speaking/practice/{session_id}").json()
        assert payload["status"] == "scored"
        assert payload["result"]["assessment_meta"]["scoring_version"]
        assert payload["result"]["overall"] is not None


def test_mock_session_turn_and_completion(monkeypatch):
    monkeypatch.setattr(settings, "stt_provider", "mock")
    monkeypatch.setattr(settings, "llm_provider", "mock")
    with TestClient(app) as client:
        topic = client.get("/api/v1/speaking/topics").json()[0]
        created = client.post(
            "/api/v1/speaking/mock-sessions",
            data={"student_name": "Mock Student", "topic_id": topic["id"]},
        )
        assert created.status_code == 200
        session_id = created.json()["id"]
        question = next(q for q in topic["questions"] if q["part"] == 1)
        with patch("app.modules.speaking.common.compress_audio", side_effect=_fake_compress), patch(
            "app.modules.speaking.mock.jobs.enqueue_speaking"
        ):
            turn = client.post(
                f"/api/v1/speaking/mock-sessions/{session_id}/turns",
                data={"part": "1", "question_id": question["id"]},
                files={"file": ("answer.webm", io.BytesIO(b"audio"), "audio/webm")},
            )
        assert turn.status_code == 200
        assert turn.json()["status"] == "pending"

        db = SessionLocal()
        try:
            db.query(SpeakingTurn).filter(SpeakingTurn.session_id == session_id).delete()
            for part in (1, 2, 3):
                result = {
                    "status": "partial", "overall": None,
                    "transcript": f"Part {part} answer about work and family today",
                    "pronun": {"score": None, "band": None},
                    "fluency": {"score": {1: 4.0, 2: 9.0, 3: 5.0}[part], "band": {1: 4.0, 2: 9.0, 3: 5.0}[part]},
                    "grammar": {"score": 6.0, "band": 6.0},
                    "vocab": {"score": 7.0, "band": 7.0},
                    "color_coded_transcript": [
                        {"id": f"w{i}", "word": word, "start": i * 0.2, "end": i * 0.2 + 0.1, "asr_probability": 0.96}
                        for i, word in enumerate(f"Part {part} answer about work and family today".split(), start=1)
                    ],
                    "uncertain_spans": [],
                }
                db.add(SpeakingTurn(
                    id=str(uuid.uuid4()), session_id=session_id, part=part,
                    sequence=part, question_text=f"Part {part}", status="completed",
                    result=result, score=6.5,
                ))
            db.commit()
        finally:
            db.close()
        completed = client.post(f"/api/v1/speaking/mock-sessions/{session_id}/complete")
        assert completed.status_code == 200
        assert completed.json()["status"] == "completed"
        assert completed.json()["result"]["status"] == "scored"
        assert completed.json()["result"]["overall"] is not None
        assert completed.json()["result"]["pronun"]["band"] is not None
        assert completed.json()["result"]["fluency"]["band"] == 6.5
        evidence_ids = completed.json()["result"]["fluency"]["evidence"]
        cited_parts = {word_id.split("_")[0] for item in evidence_ids for word_id in item["word_ids"]}
        assert cited_parts == {"t1", "t2", "t3"}
        assert set(completed.json()["result"]["fluency"]["coverage_by_part"]) == {"1", "2", "3"}


def test_database_job_processes_and_removes_work_file(tmp_path):
    db = SessionLocal()
    try:
        session = PracticeSession(
            id=str(uuid.uuid4()), student_name="Worker", part_type="PART 1",
            result={"status": "pending"},
        )
        audio = tmp_path / "job.webm"
        audio.write_bytes(b"audio")
        job = SpeakingAssessmentJob(
            id=str(uuid.uuid4()), target_type="practice", target_id=session.id,
            audio_path=str(audio), question_text="Question", task_type="PART 1",
            tier="practice", status="processing", attempts=1,
        )
        db.add_all([session, job])
        db.commit()
        job_id = job.id
        session_id = session.id
    finally:
        db.close()

    fake_result = {
        "status": "scored", "overall": 6.5, "transcript": "answer",
        "assessment_meta": {},
    }
    with patch("app.modules.speaking.assessment.engine.grade_speaking", return_value=fake_result):
        queue.process_job(job_id)
    db = SessionLocal()
    try:
        assert db.get(SpeakingAssessmentJob, job_id).status == "completed"
        assert db.get(PracticeSession, session_id).score == 6.5
        assert not audio.exists()
    finally:
        db.close()
