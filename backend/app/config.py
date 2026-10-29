import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "IoT Lab Vision Intelligence Backend"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    
    # Server configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Storage settings
    DATA_DIR: str = os.getenv("DATA_DIR", "data")
    SAVE_SNAPSHOTS: bool = False  # Set True to persist processed frames locally
    
    # Vision Model settings
    # Defaults to yolov8n.pt (nano) which Ultralytics downloads automatically if missing
    MODEL_PATH: str = os.getenv("MODEL_PATH", "models/best.pt")
    FALLBACK_MODEL: str = "yolov8n.pt"
    CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.40"))
    DEVICE: str = os.getenv("DEVICE", "cpu")  # 'cpu', 'cuda', 'mps'
    
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
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
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
