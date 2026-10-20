"""Manually exercise assignment creation with an old deadline against a temp DB."""

from scripts.diagnostics._runtime import isolated_client


def main():
    with isolated_client() as client:
        headers = {"X-Teacher-Code": "diagnostic-only"}
        created_class = client.post("/api/v1/classes", json={"name": "Sub Class"}, headers=headers)
        print("class", created_class.status_code, created_class.json())
        response = client.post(
            "/api/v1/assignments",
            headers=headers,
            data={
                "class_id": created_class.json()["id"],
                "skill": "reading",
                "title": "Past Deadline",
                "deadline": "2000-01-01T00:00:00",
            },
        )
        print("assignment", response.status_code, response.text)


if __name__ == "__main__":
    main()
