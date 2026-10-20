from sqlalchemy.orm import Session

from app.integrations.storage.blob import blob_service
from app.modules.assignments.models import Assignment
from app.modules.submissions.models import Submission


def delete_assignment_record(assignment_id: str, db: Session) -> bool:
    """Delete one assignment and its stored submission/material files."""
    assignment = db.get(Assignment, assignment_id)
    if not assignment:
        return False

    submissions = db.query(Submission).filter(Submission.assignment_id == assignment_id).all()
    for submission in submissions:
        for url in (submission.audio_url, submission.image_url):
            if url:
                try:
                    blob_service.delete_blob(url)
                except Exception:
                    pass
        db.delete(submission)

    for url in (assignment.content_file_url, assignment.audio_url):
        if url:
            try:
                blob_service.delete_blob(url)
            except Exception:
                pass

    db.delete(assignment)
    db.commit()
    return True
