from typing import List, Dict, Optional
from pydantic import BaseModel, Field

class BoundingBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float

class DetectionItem(BaseModel):
    class_name: str
    confidence: float
    box: List[float] = Field(..., description="[x1, y1, x2, y2] bounding box coordinates")
    normalized_box: Optional[List[float]] = Field(None, description="[x1, y1, x2, y2] relative to frame dimensions (0.0 to 1.0)")

class TelemetryResponse(BaseModel):
    device_id: str
    frame_index: int
    timestamp_ms: float
    inference_latency_ms: float
    total_detections: int
    equipment_counts: Dict[str, int]
    detections: List[DetectionItem]
    image_width: int
    image_height: int

class WebSocketMessage(BaseModel):
    type: str = "frame_telemetry"
    telemetry: TelemetryResponse
    annotated_frame_base64: Optional[str] = None

class HealthStatus(BaseModel):
    status: str
    model_loaded: bool
    model_path: str
    device: str
    active_ws_clients: int
    total_frames_processed: int
    uptime_seconds: float
