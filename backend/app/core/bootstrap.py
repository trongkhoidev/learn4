from sqlalchemy import inspect, text

from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from app.integrations.llm.transport import provider_readiness
from app.integrations.stt import recognition as stt
from app.modules.speaking import jobs
from app.operations import retention
from app.operations.seed import seed_speaking_data

import app.db.registry  # noqa: F401  (register all ORM models before create_all)


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)
    # Preserve the existing additive bootstrap for databases predating `classes.level`.
    if "level" not in {column["name"] for column in inspect(engine).get_columns("classes")}:
        with engine.begin() as connection:
            connection.execute(text(
                "ALTER TABLE classes ADD COLUMN level VARCHAR(80) NOT NULL DEFAULT 'General English B1'"
            ))


def start_runtime() -> None:
    initialize_database()
    seed_speaking_data()
    if settings.whisper_preload:
        stt.preload()
    jobs.start_worker()
    retention.start()


def stop_runtime() -> None:
    retention.stop()
    jobs.stop_worker()


def readiness() -> dict:
    stt_state = stt.readiness()
    llm_state = provider_readiness()
    worker_state = jobs.readiness()
    ready = stt_state["ready"] and llm_state["ready"] and worker_state["ready"]
    return {
        "status": "ready" if ready else "not_ready",
        "stt": stt_state,
        "llm": llm_state,
        "queue": worker_state,
    }
