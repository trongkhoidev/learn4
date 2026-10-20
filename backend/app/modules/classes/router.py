import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.access import verify_teacher
from app.modules.assignments.models import Assignment
from app.modules.assignments.use_cases import delete_assignment_record
from app.modules.classes.models import Class
from app.modules.classes.schemas import ClassCreate, ClassOut, ClassUpdate

router = APIRouter(prefix="/api/v1", tags=["classes"])

_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _gen_code() -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(6))


@router.post("/classes", response_model=ClassOut, dependencies=[Depends(verify_teacher)])
def create_class(payload: ClassCreate, db: Session = Depends(get_db)):
    code = _gen_code()
    for _ in range(20):
        if not db.query(Class).filter(Class.share_code == code).first():
            break
        code = _gen_code()
    cls = Class(name=payload.name, level=payload.level, teacher_note=payload.teacher_note, share_code=code)
    db.add(cls)
    db.commit()
    db.refresh(cls)
    return cls


@router.get("/classes", response_model=list[ClassOut], dependencies=[Depends(verify_teacher)])
def list_classes(db: Session = Depends(get_db)):
    return db.query(Class).order_by(Class.created_at.desc()).all()


@router.get("/classes/{class_id}", response_model=ClassOut)
def get_class(class_id: str, db: Session = Depends(get_db)):
    cls = db.get(Class, class_id)
    if not cls:
        raise HTTPException(404, "Không tìm thấy lớp")
    return cls


@router.get("/join", response_model=ClassOut)
def join(code: str, db: Session = Depends(get_db)):
    cls = db.query(Class).filter(Class.share_code == code).first()
    if not cls:
        raise HTTPException(404, "Mã lớp không hợp lệ")
    return cls


@router.patch("/classes/{class_id}", response_model=ClassOut, dependencies=[Depends(verify_teacher)])
def update_class(class_id: str, payload: ClassUpdate, db: Session = Depends(get_db)):
    cls = db.get(Class, class_id)
    if not cls:
        raise HTTPException(404, "Không tìm thấy lớp")
    
    if payload.name is not None:
        cls.name = payload.name
    if payload.level is not None:
        cls.level = payload.level
    if payload.teacher_note is not None:
        cls.teacher_note = payload.teacher_note
        
    db.commit()
    db.refresh(cls)
    return cls


@router.delete("/classes/{class_id}", dependencies=[Depends(verify_teacher)])
def delete_class(class_id: str, db: Session = Depends(get_db)):
    cls = db.get(Class, class_id)
    if not cls:
        raise HTTPException(404, "Không tìm thấy lớp")
        
    assignments = db.query(Assignment).filter(Assignment.class_id == class_id).all()
    for assignment in assignments:
        delete_assignment_record(assignment.id, db)
        
    db.delete(cls)
    db.commit()
    return {"ok": True}
