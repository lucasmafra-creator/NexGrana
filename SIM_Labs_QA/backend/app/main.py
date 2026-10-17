from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .config import settings
from .qa_environment import enforce_qa_environment
from .db import Base, engine, SessionLocal
from .seed import seed
from . import integration_models, engine_models, promotion_models
from .routers.promotions import router as promotions_router
from .routers.engine import router as engine_router
from .local_auth import router as auth_router
from .routers.integrated import router as integrated_router
from .routers.core import router as core_router
from .routers.live import router as live_router
from .routers.qa_pipeline import router as qa_pipeline_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    enforce_qa_environment()
    if settings.auto_init_db and settings.is_dev:
        Base.metadata.create_all(engine)
        with SessionLocal() as db:
            seed(db)
    yield


app = FastAPI(title="SIM Labs Control Center QA", version="0.4.1-qa.2-engine", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[x.strip() for x in settings.cors_origins.split(",") if x.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Dev-Actor", "X-SIM-Ingest-Token"],
)
app.include_router(promotions_router, prefix="/api/v1")
app.include_router(engine_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(integrated_router, prefix="/api/v1")
app.include_router(core_router, prefix="/api/v1")
app.include_router(live_router, prefix="/api/v1")
app.include_router(qa_pipeline_router, prefix="/api/v1")

static_dir = Path(__file__).resolve().parents[1] / "static"
if (static_dir / "index.html").exists():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
