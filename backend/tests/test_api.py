import json

import pytest
from fastapi.testclient import TestClient

from app.main import app

TEACHER_HEADERS = {"X-Teacher-Code": "test-code"}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def class_id(client):
    resp = client.post("/api/v1/classes", json={"name": "IELTS 7.0"}, headers=TEACHER_HEADERS)
    assert resp.status_code == 200
    return resp.json()["id"]


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_join(client, class_id):
    cls = client.get(f"/api/v1/classes/{class_id}").json()
    joined = client.get(f"/api/v1/join?code={cls['share_code']}")
    assert joined.status_code == 200
    assert joined.json()["id"] == class_id


def test_reading_flow_end_to_end(client, class_id):
    resp = client.post(
        "/api/v1/assignments",
        data={
            "class_id": class_id,
            "skill": "reading",
            "title": "Test 1",
            "question_count": "3",
            "answer_key": json.dumps(["A", "TRUE", "modern"]),
        },
        headers=TEACHER_HEADERS,
    )
    assert resp.status_code == 200
    assignment = resp.json()
    assert assignment["answer_key"] == ["A", "TRUE", "modern"]

    student_view = client.get(f"/api/v1/assignments/{assignment['id']}")
    assert student_view.status_code == 200
    assert "answer_key" not in student_view.json()

    sub = client.post(
        f"/api/v1/assignments/{assignment['id']}/submit",
        data={"student_name": "Minh Anh", "answers": json.dumps(["A", "TRUE", "modern"])},
    )
    assert sub.status_code == 200
    assert sub.json()["status"] == "graded"
    assert sub.json()["score"] == 3

    subs = client.get(f"/api/v1/assignments/{assignment['id']}/submissions", headers=TEACHER_HEADERS)
    assert len(subs.json()) == 1

    roster = client.get(f"/api/v1/classes/{class_id}/roster?name=Minh Anh")
    assert len(roster.json()) == 1


def test_teacher_auth_required(client):
    assert client.post("/api/v1/classes", json={"name": "X"}).status_code == 403


def test_update_and_delete(client, class_id):
    resp = client.post(
        "/api/v1/assignments",
        data={
            "class_id": class_id,
            "skill": "writing",
            "title": "Writing Task 1",
            "min_words": 150
        },
        headers=TEACHER_HEADERS,
    )
    assert resp.status_code == 200
    assignment_id = resp.json()["id"]
    
    resp = client.patch(
        f"/api/v1/assignments/{assignment_id}",
        data={"title": "Updated Title", "min_words": 200},
        headers=TEACHER_HEADERS
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Title"
    assert resp.json()["min_words"] == 200
    
    resp = client.patch(
        f"/api/v1/classes/{class_id}",
        json={"name": "IELTS 7.5"},
        headers=TEACHER_HEADERS
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "IELTS 7.5"
    
    roster = client.get(f"/api/v1/classes/{class_id}/roster?name=Minh Anh")
    assert roster.status_code == 200
    if len(roster.json()) > 0:
        assert "assignment_title" in roster.json()[0]
    
    resp = client.delete(f"/api/v1/assignments/{assignment_id}", headers=TEACHER_HEADERS)
    assert resp.status_code == 200
    
    resp = client.delete(f"/api/v1/classes/{class_id}", headers=TEACHER_HEADERS)
    assert resp.status_code == 200
