"""UrbanEye FastAPI backend.  Run:  uvicorn app.main:app --reload  (from the backend folder)."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import db
from .config import settings
from .history_routes import router as history_router
from .models import registry
from .routes import router
from .satellite_routes import router as satellite_router
from .services.satellite import new_client

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    registry.load()
    app.state.http = new_client()      # shared connection pool for satellite tile downloads
    yield
    await app.state.http.aclose()


app = FastAPI(title="UrbanEye API", version="1.0.0", lifespan=lifespan,
              description="Satellite-image land-cover segmentation (U-Net++), object detection "
                          "(YOLO11 / Roboflow) and environmental-impact analysis.")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                   allow_methods=["GET", "POST", "DELETE"], allow_headers=["*"])
app.include_router(router)
app.include_router(satellite_router)
app.include_router(history_router)


@app.get("/")
def root():
    return {"name": "UrbanEye API", "docs": "/docs", "health": "/api/health"}
