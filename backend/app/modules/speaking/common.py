"""HTTP input and audio preparation shared by Speaking Practice and Mock."""

import tempfile
import uuid
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.integrations.audio.processor import compress_audio, probe_audio_duration
from app.integrations.storage.blob import blob_service
from app.modules.speaking.models import SpeakingQuestion


def normalize_student_name(value: str) -> str:
    name = " ".join((value or "").strip().split())
    if not name:
        raise HTTPException(422, "Tên học viên không hợp lệ")
    return name


def student_name_key(value: str) -> str:
    return normalize_student_name(value).lower()


def resolve_question(db, question_id, topic_id, question_text, part=None):
    text = question_text or "Describe a topic you know well"
    question = None
    if question_id:
        question = db.get(SpeakingQuestion, question_id)
        if not question:
            raise HTTPException(404, "Không tìm thấy câu hỏi Speaking")
        if topic_id and question.topic_id != topic_id:
            raise HTTPException(422, "Câu hỏi không thuộc chủ đề đã chọn")
        if part and question.part != part:
            raise HTTPException(422, "Câu hỏi không thuộc part đã chọn")
        text = question.question_text
    return question, text


async def prepare_audio(
    file: UploadFile, *, keep_for_job: bool, max_seconds: Optional[int] = None,
) -> tuple[str, str]:
    if file.content_type and not file.content_type.startswith("audio/"):
        raise HTTPException(415, "Tệp tải lên phải là audio")
    data = await file.read(settings.max_audio_bytes + 1)
    if not data:
        raise HTTPException(422, "File audio rỗng")
    if len(data) > settings.max_audio_bytes:
        raise HTTPException(413, "File audio vượt quá giới hạn cho phép")

    suffix = Path(file.filename or "audio.webm").suffix or ".webm"
    raw = tempfile.NamedTemporaryFile(prefix="lexilearn-speaking-", suffix=suffix, delete=False)
    raw.write(data)
    raw.close()
    encoded = tempfile.NamedTemporaryFile(prefix="lexilearn-speaking-", suffix=".webm", delete=False)
    encoded.close()
    prepared = False
    try:
        try:
            await run_in_threadpool(compress_audio, raw.name, encoded.name)
        except Exception as exc:
            raise HTTPException(422, f"Không thể đọc file audio: {exc}")
        duration = probe_audio_duration(encoded.name)
        if settings.stt_provider != "mock" and duration is None:
            raise HTTPException(422, "Không xác định được thời lượng audio")
        duration_limit = min(settings.max_audio_seconds, max_seconds or settings.max_audio_seconds)
        if duration is not None and duration > duration_limit:
            raise HTTPException(413, "Audio vượt quá thời lượng cho phép")

        object_key = f"speaking/{uuid.uuid4()}.webm"
        with open(encoded.name, "rb") as audio_file:
            audio_url = blob_service.upload_bytes(object_key, audio_file.read(), "audio/webm")
        if keep_for_job:
            job_dir = Path(settings.storage_dir) / "speaking-jobs"
            job_dir.mkdir(parents=True, exist_ok=True)
            persistent = job_dir / f"{uuid.uuid4()}.webm"
            Path(encoded.name).replace(persistent)
            prepared = True
            return str(persistent), audio_url
        prepared = True
        return encoded.name, audio_url
    finally:
        Path(raw.name).unlink(missing_ok=True)
        if keep_for_job or not prepared:
            Path(encoded.name).unlink(missing_ok=True)
