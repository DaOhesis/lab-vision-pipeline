from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.routes import router as api_router
from app.services.detector import detector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("backend.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Application startup: Pre-warm model in memory
    logger.info("Initializing IoT Lab Vision Pipeline Backend...")
    logger.info(f"Model status: Loaded ({detector.active_model_path}) on {settings.DEVICE}")
    yield
    # Application shutdown
    logger.info("Shutting down Vision Pipeline Backend...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Local computer vision ingestion and real-time inference server for ESP32-CAM lab equipment monitoring.",
    lifespan=lifespan
)

# Enable CORS for Next.js frontend running locally
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Mount API routes
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
app.include_router(api_router)  # Also mount root /health and /ws/stream

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
