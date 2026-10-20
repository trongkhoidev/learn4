"""Application router registry. Imported once by the FastAPI entrypoint."""

from app.modules.assignments.router import router as assignments_router
from app.modules.classes.router import router as classes_router
from app.modules.speaking.router import router as speaking_router
from app.modules.submissions.router import router as submissions_router

routers = [classes_router, assignments_router, submissions_router, speaking_router]
