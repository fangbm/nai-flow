"""NAI Flow API server. Run: uvicorn main:app --reload --port 8000"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import router


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.load()
    yield


app = FastAPI(title="NAI Flow API", version="0.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)
app.include_router(router)
