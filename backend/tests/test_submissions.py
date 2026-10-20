import pytest
import json
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_submit_deadline_and_normal_reading(client):
    headers = {"X-Teacher-Code": settings.teacher_access_code}
    res = client.post("/api/v1/classes", json={"name": "Sub Class"}, headers=headers)
    class_id = res.json()["id"]

    # Past deadline
    res_assign_past = client.post(
        "/api/v1/assignments",
        headers=headers,
        data={
            "class_id": class_id,
            "skill": "reading",
            "title": "Past Deadline",
            "deadline": "2000-01-01T00:00:00"
        }
    )
    assign_past_id = res_assign_past.json()["id"]

    # Submit past deadline
    res_sub_past = client.post(
        f"/api/v1/assignments/{assign_past_id}/submit",
        data={"student_name": "  TeStEr  "}
    )
    assert res_sub_past.status_code == 400
    assert "quá hạn" in res_sub_past.json()["detail"].lower()

    # Normal assignment without deadline
    res_assign = client.post(
        "/api/v1/assignments",
        headers=headers,
        data={
            "class_id": class_id,
            "skill": "reading",
            "title": "Normal Reading",
            "answer_key": json.dumps(["A", "B"])
        }
    )
    assign_id = res_assign.json()["id"]

    # Submit reading
    res_sub = client.post(
        f"/api/v1/assignments/{assign_id}/submit",
        data={
            "student_name": "  TeStEr  ",
            "answers": json.dumps(["A", "C"])
        }
    )
    assert res_sub.status_code == 200
    sub_data = res_sub.json()
    assert sub_data["student_name"] == "tester"  # Checked normalization
    assert sub_data["status"] == "graded"
    assert sub_data["score"] == 1.0  # 1 correct out of 2
