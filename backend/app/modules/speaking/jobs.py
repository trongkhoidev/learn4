"""Small durable database-backed queue for Speaking assessment.

This removes request-lifetime coupling and survives API restarts. It is suitable
for the current single-worker deployment. Multi-host production can replace the
adapter with Redis/Arq without changing router contracts.
"""

import logging
import os
import threading
import uuid
from datetime import datetime, timezone

from app.core.config import settings
from app.db.session import SessionLocal
from app.modules.speaking.models import (
    PracticeSession, SpeakingAssessmentJob, SpeakingTurn,
)
from app.modules.submissions.models import Submission

logger = logging.getLogger(__name__)
_stop_event = threading.Event()
_wake_event = threading.Event()
_worker = None
_worker_lock = threading.Lock()


def enqueue_speaking(
    db,
    *,
    target_type: str,
    target_id: str,
    audio_path: str,
    question_text: str,
    task_type: str,
    tier: str,
) -> SpeakingAssessmentJob:
    if target_type not in {"practice", "turn", "submission"}:
        raise ValueError("Unsupported speaking job target")
    job = SpeakingAssessmentJob(
        id=str(uuid.uuid4()),
        target_type=target_type,
        target_id=target_id,
        audio_path=audio_path,
        question_text=question_text,
        task_type=task_type,
        tier=tier,
        status="pending",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    _wake_event.set()
    return job


def _claim_next():
    db = SessionLocal()
    try:
        job = (
            db.query(SpeakingAssessmentJob)
            .filter(SpeakingAssessmentJob.status == "pending")
            .order_by(SpeakingAssessmentJob.created_at.asc())
            .first()
        )
        if not job:
            return None
        job.status = "processing"
        job.attempts = (job.attempts or 0) + 1
        db.commit()
        return job.id
    finally:
        db.close()


def _finish_target(db, job, result):
    now = datetime.now(timezone.utc)
    if job.target_type == "practice":
        target = db.get(PracticeSession, job.target_id)
        if target:
            target.result = result
            target.transcript = result.get("transcript")
            target.score = result.get("overall")
    elif job.target_type == "turn":
        target = db.get(SpeakingTurn, job.target_id)
        if target:
            target.result = result
            target.transcript = result.get("transcript")
            target.score = result.get("overall")
            target.status = "completed" if result.get("status") == "scored" else result.get("status", "failed")
            target.completed_at = now
    else:
        target = db.get(Submission, job.target_id)
        if target:
            target.result = result
            target.transcript = result.get("transcript")
            target.score = result.get("overall")
            target.status = "graded"


def process_job(job_id: str):
    from .assessment.engine import failed_result, grade_speaking

    db = SessionLocal()
    job = db.get(SpeakingAssessmentJob, job_id)
    if not job:
        db.close()
        return
    final_attempt = (job.attempts or 0) >= settings.speaking_job_max_attempts
    try:
        model = {"practice": PracticeSession, "turn": SpeakingTurn, "submission": Submission}[job.target_type]
        target = db.get(model, job.target_id)
        recognition_context = (target.result or {}).get("recognition_context", "") if target else ""
        result = grade_speaking(
            job.audio_path, job.question_text, job.task_type, job.tier,
            **({"recognition_context": recognition_context} if recognition_context else {}),
        )
        result.setdefault("assessment_meta", {})
        result["assessment_meta"].update({
            "scoring_version": settings.scoring_version,
            "stt_profile_version": settings.stt_profile_version,
        })
        _finish_target(db, job, result)
        job.status = "completed"
        job.error = None
        db.commit()
        try:
            os.remove(job.audio_path)
        except OSError:
            pass
    except Exception as exc:
        db.rollback()
        job = db.get(SpeakingAssessmentJob, job_id)
        if job:
            job.error = str(exc)[:2000]
            job.status = "failed" if final_attempt else "pending"
            if final_attempt:
                failure = failed_result("assessment_processing_failed", str(exc)[:500])
                _finish_target(db, job, failure)
                try:
                    os.remove(job.audio_path)
                except OSError:
                    pass
            db.commit()
        logger.exception("Speaking job %s failed", job_id)
    finally:
        db.close()


def _worker_loop():
    while not _stop_event.is_set():
        job_id = _claim_next()
        if job_id:
            process_job(job_id)
            continue
        _wake_event.wait(settings.speaking_job_poll_seconds)
        _wake_event.clear()


def start_worker():
    global _worker
    with _worker_lock:
        if _worker and _worker.is_alive():
            return _worker
        db = SessionLocal()
        try:
            db.query(SpeakingAssessmentJob).filter(
                SpeakingAssessmentJob.status == "processing"
            ).update({SpeakingAssessmentJob.status: "pending"}, synchronize_session=False)
            db.commit()
        finally:
            db.close()
        _stop_event.clear()
        _worker = threading.Thread(
            target=_worker_loop, name="speaking-assessment-worker", daemon=True,
        )
        _worker.start()
        return _worker


def stop_worker():
    _stop_event.set()
    _wake_event.set()
    worker = _worker
    if worker and worker.is_alive():
        worker.join(timeout=5)


def readiness() -> dict:
    worker = _worker
    return {"ready": bool(worker and worker.is_alive()), "name": "speaking-assessment-worker"}
