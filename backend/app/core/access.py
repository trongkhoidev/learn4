from fastapi import Header, HTTPException

from .config import settings


def verify_teacher(x_teacher_code: str | None = Header(default=None)) -> None:
    if not settings.teacher_access_code:
        return
    if x_teacher_code != settings.teacher_access_code:
        raise HTTPException(status_code=403, detail="Sai mã giáo viên")
