"""Audio retention worker for stored learner recordings and orphan job files."""

import logging
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.core.config import settings
from app.db.session import SessionLocal
from app.modules.speaking.models import PracticeSession, SpeakingTurn
from app.modules.submissions.models import Submission
from app.integrations.storage.blob import blob_service

logger = logging.getLogger(__name__)
_stop = threading.Event()
_thread = None


def cleanup_expired() -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.audio_retention_days)
    deleted = 0
    db = SessionLocal()
    try:
        targets = [
            (PracticeSession, PracticeSession.created_at),
            (SpeakingTurn, SpeakingTurn.created_at),
            (Submission, Submission.submitted_at),
        ]
        for model, date_column in targets:
            rows = db.query(model).filter(
                date_column < cutoff, model.audio_url.isnot(None)
            ).all()
            for row in rows:
                try:
                    blob_service.delete_blob(row.audio_url)
                except Exception as exc:
                    logger.warning("Could not delete retained audio %s: %s", row.audio_url, exc)
                    continue
                row.audio_url = None
                deleted += 1
        db.commit()
    finally:
        db.close()

    job_dir = Path(settings.storage_dir) / "speaking-jobs"
    if job_dir.exists():
        threshold = (datetime.now(timezone.utc) - timedelta(hours=settings.speaking_job_orphan_hours)).timestamp()
        for path in job_dir.glob("*.webm"):
            try:
                if path.stat().st_mtime < threshold:
                    path.unlink(missing_ok=True)
            except OSError:
                pass
    return {"deleted_audio_objects": deleted, "cutoff": cutoff.isoformat()}


def _loop():
    while not _stop.is_set():
        try:
            cleanup_expired()
        except Exception:
            logger.exception("Audio retention cleanup failed")
        _stop.wait(24 * 60 * 60)


def start():
    global _thread
    if _thread and _thread.is_alive():
        return
    _stop.clear()
    _thread = threading.Thread(target=_loop, name="audio-retention-worker", daemon=True)
    _thread.start()


def stop():
    _stop.set()
    if _thread and _thread.is_alive():
        _thread.join(timeout=5)
