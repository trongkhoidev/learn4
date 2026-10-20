"""Helpers for diagnostics that must never touch the configured local database."""

from contextlib import contextmanager
import os
from tempfile import TemporaryDirectory
from pathlib import Path


@contextmanager
def isolated_client():
    """Start the app with a disposable SQLite DB, storage, and mock providers."""
    with TemporaryDirectory(prefix="lexilearn-diagnostic-") as directory:
        root = Path(directory)
        os.environ.update({
            "DATABASE_URL": f"sqlite:///{root / 'diagnostic.db'}",
            "STORAGE_DIR": str(root / "storage"),
            "TEACHER_ACCESS_CODE": "diagnostic-only",
            "STT_PROVIDER": "mock",
            "LLM_PROVIDER": "mock",
            "GROQ_API_KEY": "",
            "GOOGLE_API_KEY": "",
            "R2_ENDPOINT_URL": "",
            "R2_ACCESS_KEY_ID": "",
            "R2_SECRET_ACCESS_KEY": "",
            "WHISPER_PRELOAD": "false",
        })
        from fastapi.testclient import TestClient
        from app.main import app

        with TestClient(app) as client:
            yield client
