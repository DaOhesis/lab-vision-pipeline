import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "IoT Lab Vision Intelligence Backend"
    VERSION: str = "1.1.0"
    API_V1_PREFIX: str = "/api/v1"
    
    # Server configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Storage settings
    DATA_DIR: str = os.getenv("DATA_DIR", "data")
    SAVE_SNAPSHOTS: bool = False  # Set True to persist processed frames locally
    
    # Vision Model settings
    # Primary model path (custom weights if available)
    MODEL_PATH: str = os.getenv("MODEL_PATH", "models/best.pt")
    # Default high-accuracy backbone: YOLO11 Small (significantly superior mAP to nano)
    FALLBACK_MODEL: str = os.getenv("FALLBACK_MODEL", "models/yolo11s.pt")
    CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.45"))
    IOU_THRESHOLD: float = float(os.getenv("IOU_THRESHOLD", "0.45"))
    AGNOSTIC_NMS: bool = bool(int(os.getenv("AGNOSTIC_NMS", "1")))
    DEVICE: str = os.getenv("DEVICE", "cpu")  # 'cpu', 'cuda', 'mps'
    
    # Temporal Smoothing & Stability
    ENABLE_TRACKER: bool = True
    TRACKER_SMOOTHING_ALPHA: float = 0.70  # EMA smoothing factor for bboxes (0.0 - 1.0)
    TRACKER_MAX_MISSED_FRAMES: int = 2     # Keep object alive across transient dropped frames
    MIN_CONSECUTIVE_FRAMES: int = 2        # Require 2 frames for low-conf detections to prevent 1-frame false alarms
    
    # Target Lab Equipment Taxonomy
    LAB_CLASSES: List[str] = [
        "3d_printer",
        "dell_monitor",
        "microcontroller",
        "oscilloscope",
        "soldering_station"
    ]

    # Local LLM Agent settings (Ollama)
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "lfm3:1.7b")
    OLLAMA_TIMEOUT: float = float(os.getenv("OLLAMA_TIMEOUT", "15.0"))
    
    # CORS Origins for Frontend Integration
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ]

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
