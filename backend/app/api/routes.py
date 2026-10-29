import time
import base64
import asyncio
import logging
from typing import Optional
from fastapi import APIRouter, Request, Header, WebSocket, WebSocketDisconnect, HTTPException, Response
from fastapi.responses import JSONResponse

from app.config import settings
from app.services.detector import detector
from app.services.stream_manager import stream_manager
from app.services.llm_agent import llm_agent
from app.services.commentary_engine import commentary_engine
from app.api.schemas import (
    HealthStatus,
    TelemetryResponse,
    AgentQueryRequest,
    AgentQueryResponse,
    AgentBriefingResponse
)

router = APIRouter()
logger = logging.getLogger("uvicorn.error")

server_start_time = time.time()
processed_frames_count = 0

@router.post("/telemetry/frame", response_model=TelemetryResponse)
async def ingest_frame(
    request: Request,
    x_device_id: Optional[str] = Header("unknown_device"),
    x_frame_index: Optional[int] = Header(0),
    x_timestamp_ms: Optional[float] = Header(None)
):
    """
    Ingests a raw JPEG frame directly from ESP32-CAM or edge simulation script.
    Executes asynchronous YOLO inference and broadcasts telemetry over WebSockets.
    """
    global processed_frames_count
    
    # Read raw body bytes
    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Empty request payload. Expected raw JPEG stream.")

    # Offload inference to worker thread to keep the asyncio event loop responsive
    try:
        summary, annotated_bytes = await asyncio.to_thread(detector.detect, body)
    except Exception as e:
        logger.error(f"[Ingest] Error during image decoding or inference: {e}")
        raise HTTPException(status_code=422, detail=f"Frame processing failed: {str(e)}")

    processed_frames_count += 1
    timestamp = x_timestamp_ms if x_timestamp_ms is not None else round(time.time() * 1000, 2)

    telemetry_data = {
        "device_id": x_device_id,
        "frame_index": x_frame_index,
        "timestamp_ms": timestamp,
        "latest_commentary": commentary_engine.last_commentary,
        **summary
    }

    # Store latest state in memory
    await stream_manager.update_latest(telemetry_data, annotated_bytes)

    # Convert annotated image to base64 for unified WebSocket payload
    base64_frame = base64.b64encode(annotated_bytes).decode("utf-8")
    
    # Non-blocking broadcast of frame telemetry to all active Next.js dashboard clients
    asyncio.create_task(stream_manager.broadcast({
        "type": "frame_update",
        "telemetry": telemetry_data,
        "annotated_frame_base64": f"data:image/jpeg;base64,{base64_frame}"
    }))

    # Non-blocking event analysis for live stream commentary
    async def handle_commentary():
        commentary = await commentary_engine.process_frame_detections(summary.get("detections", []))
        if commentary:
            await stream_manager.broadcast({
                "type": "live_commentary",
                "commentary": commentary
            })

    asyncio.create_task(handle_commentary())

    return JSONResponse(status_code=200, content=telemetry_data)

@router.get("/telemetry/latest")
async def get_latest_telemetry():
    """Returns the most recent detection telemetry metadata."""
    if stream_manager.latest_telemetry is None:
        return JSONResponse(status_code=404, content={"message": "No frames ingested yet."})
    return stream_manager.latest_telemetry

@router.get("/telemetry/latest/frame")
async def get_latest_frame():
    """Returns the most recent annotated JPEG frame."""
    if stream_manager.latest_annotated_frame_bytes is None:
        raise HTTPException(status_code=404, detail="No frames ingested yet.")
    return Response(content=stream_manager.latest_annotated_frame_bytes, media_type="image/jpeg")

@router.get("/inventory/summary")
async def get_inventory_summary():
    """Returns active counts of detected laboratory equipment."""
    if stream_manager.latest_telemetry is None:
        return {cls_name: 0 for cls_name in settings.LAB_CLASSES}
    
    counts = stream_manager.latest_telemetry.get("equipment_counts", {})
    # Ensure all target lab classes are represented even if count is 0
    full_inventory = {cls_name: counts.get(cls_name, 0) for cls_name in settings.LAB_CLASSES}
    return {
        "inventory": full_inventory,
        "total_active_items": sum(full_inventory.values()),
        "last_updated_timestamp": stream_manager.latest_telemetry.get("timestamp_ms")
    }

@router.websocket("/ws/stream")
async def websocket_stream_endpoint(websocket: WebSocket):
    """
    Full-duplex WebSocket connection for real-time Next.js dashboard streaming.
    Streams detections, bounding boxes, and base64 frames.
    """
    await stream_manager.connect(websocket)
    try:
        while True:
            # Keep connection open; receive ping or client commands
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        stream_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"[WS] Connection exception: {e}")
        stream_manager.disconnect(websocket)

@router.get("/commentary/latest")
async def get_latest_commentary():
    """Returns the most recent AI commentary message."""
    if commentary_engine.last_commentary is None:
        return JSONResponse(status_code=200, content={"commentary": None, "message": "No action events detected yet."})
    return {"commentary": commentary_engine.last_commentary}

@router.get("/commentary/history")
async def get_commentary_history():
    """Returns recent stream narration and action commentary history."""
    return {"history": commentary_engine.commentary_history}

@router.get("/health", response_model=HealthStatus)
async def health_check():
    """System health check and diagnostic information."""
    return HealthStatus(
        status="healthy",
        model_loaded=detector.model is not None,
        model_path=detector.active_model_path,
        device=settings.DEVICE,
        active_ws_clients=len(stream_manager.active_connections),
        total_frames_processed=processed_frames_count,
        uptime_seconds=round(time.time() - server_start_time, 2)
    )

@router.get("/model/info")
async def get_model_info():
    """Returns active YOLO model details, available models, and thresholds."""
    available = []
    for m in ["models/best.pt", "models/yolo11s.pt", "models/yolo11n.pt", "models/yolo11m.pt", "yolo11s.pt", "yolo11n.pt", "yolov8n.pt"]:
        if os.path.exists(m):
            available.append(os.path.basename(m))
    return {
        "active_model": os.path.basename(detector.active_model_path),
        "active_model_path": detector.active_model_path,
        "confidence_threshold": detector.confidence_threshold,
        "iou_threshold": detector.iou_threshold,
        "tracker_enabled": settings.ENABLE_TRACKER,
        "device": settings.DEVICE,
        "available_models": list(dict.fromkeys(available))
    }

@router.post("/model/select")
async def select_model(request: Request):
    """Dynamically switches the active YOLO model weights."""
    data = await request.json()
    model_name = data.get("model_name", "yolo11s.pt")
    success = detector.switch_model(model_name)
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to load model {model_name}")
    return {
        "status": "success",
        "active_model": os.path.basename(detector.active_model_path)
    }

@router.post("/model/settings")
async def update_model_settings(request: Request):
    """Updates model inference parameters at runtime."""
    data = await request.json()
    if "confidence_threshold" in data:
        detector.confidence_threshold = max(0.1, min(0.95, float(data["confidence_threshold"])))
    if "iou_threshold" in data:
        detector.iou_threshold = max(0.1, min(0.95, float(data["iou_threshold"])))
    return {
        "status": "updated",
        "confidence_threshold": detector.confidence_threshold,
        "iou_threshold": detector.iou_threshold
    }

@router.post("/agent/query", response_model=AgentQueryResponse)
async def query_lab_agent(request: AgentQueryRequest):
    """
    Asks the local SLM agent (Qwen 2.5 1.5B via Ollama) a natural language question
    grounded strictly in the live laboratory computer vision scene.
    """
    answer, model_name, latency = await llm_agent.answer_query(
        question=request.question,
        telemetry=stream_manager.latest_telemetry,
        history=request.history
    )
    return AgentQueryResponse(
        answer=answer,
        model_used=model_name,
        latency_ms=latency,
        timestamp=time.time()
    )

@router.get("/agent/briefing", response_model=AgentBriefingResponse)
async def get_lab_briefing():
    """
    Generates an automated executive situation report and safety assessment
    synthesized by the local SLM based on the latest detected equipment.
    """
    summary, safety_eval, safety_status, model_name, latency = await llm_agent.generate_briefing(
        telemetry=stream_manager.latest_telemetry
    )
    counts = stream_manager.latest_telemetry.get("equipment_counts", {}) if stream_manager.latest_telemetry else {}

    return AgentBriefingResponse(
        summary=summary,
        safety_assessment=safety_eval,
        safety_status=safety_status,
        equipment_tally=counts,
        model_used=model_name,
        latency_ms=latency,
        timestamp=time.time()
    )
