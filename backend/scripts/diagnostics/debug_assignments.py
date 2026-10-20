"""Manually exercise teacher class and assignment creation against a temp DB."""

from scripts.diagnostics._runtime import isolated_client


def main():
    with isolated_client() as client:
        headers = {"X-Teacher-Code": "diagnostic-only"}
        created_class = client.post("/api/v1/classes", json={"name": "Debug Class"}, headers=headers)
        print("class", created_class.status_code, created_class.json())
        class_id = created_class.json()["id"]
        assignment = client.post(
            "/api/v1/assignments",
            headers=headers,
            data={"class_id": class_id, "skill": "reading", "title": "Debug Reading"},
            files={"content_file": ("test.pdf", b"%PDF-1.4\\n% diagnostic sample\\n", "application/pdf")},
        )
        print("assignment", assignment.status_code, assignment.json())


if __name__ == "__main__":
    main()
