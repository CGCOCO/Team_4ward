from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.analyze import router as analysis_router
from app.privacy.image_masker import initialize_yolo_models


@asynccontextmanager
async def lifespan(app: FastAPI):
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
    analysis_router,
    prefix="/api/v1/analyze",
    tags=["analyze"]
)

@app.get("/health")
def connection_check():
    return {"status": "healthy"}
