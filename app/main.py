from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.auth import router as auth_router
from app.api.analyze import router as analysis_router
from app.api.advisor import router as advisor_router
from app.config import configure_logging, validate_settings
from app.db import init_db
from app.privacy.image_masker import initialize_yolo_models

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_settings()
    init_db()
    initialize_yolo_models()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    auth_router,
    prefix="/api/v1/auth",
    tags=["auth"]
)

app.include_router(
    analysis_router,
    prefix="/api/v1/analyze",
    tags=["analyze"]
)

app.include_router(
    advisor_router,
    prefix="/api/v1/advisor",
    tags=["advisor"]
)

@app.get("/health")
def connection_check():
    return {"status": "healthy"}
