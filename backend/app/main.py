import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exc()
    print(f"ERROR on {request.method} {request.url}: {exc}\n{tb}", flush=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Lỗi máy chủ nội bộ: {str(exc)}", "traceback": tb},
    )


@app.get("/")
def index():
    return {
        "service": "LexiLearn Backend API",
        "status": "online",
        "frontend": "https://learn4-app.vercel.app",
        "docs": "/docs",
        "health": "/health",
        "ready": "/ready",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    return readiness()
