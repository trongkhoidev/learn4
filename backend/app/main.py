from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.bootstrap import readiness, start_runtime, stop_runtime
from app.core.config import settings
from app.modules.registry import routers

@asynccontextmanager
async def lifespan(app: FastAPI):
    start_runtime()
    try:
        yield
    finally:
        stop_runtime()


app = FastAPI(title="LexiLearn API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in routers:
    app.include_router(r)

app.mount("/storage", StaticFiles(directory=settings.storage_dir, check_dir=False), name="storage")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    return readiness()
