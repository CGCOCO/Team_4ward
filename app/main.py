from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.analyze import router as analysis_router


app = FastAPI()

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