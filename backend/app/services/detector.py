import os
import time
import logging
from typing import List, Dict, Any, Tuple
import numpy as np
import cv2
from ultralytics import YOLO

from app.config import settings

logger = logging.getLogger("uvicorn.error")

class VisionDetector:
    """
    Thread-safe YOLO inference engine for IoT Lab Equipment Detection.
    Loads custom fine-tuned weights (best.pt) or falls back to yolov8n.pt for initial testing.
    """
    def __init__(self):
        self.model = None
        self.active_model_path = ""
        self.total_inferences = 0
        self._initialize_model()

    def _initialize_model(self):
        # Priority: configured model path -> fallback nano model
        chosen_path = settings.MODEL_PATH if os.path.exists(settings.MODEL_PATH) else settings.FALLBACK_MODEL
        logger.info(f"[VisionEngine] Initializing YOLO model from: {chosen_path} (Target device: {settings.DEVICE})")
        
        try:
            self.model = YOLO(chosen_path)
            self.active_model_path = chosen_path
            logger.info(f"[VisionEngine] Model successfully loaded into memory: {chosen_path}")
        except Exception as e:
            logger.error(f"[VisionEngine] Error loading model from {chosen_path}: {e}")
            if chosen_path != settings.FALLBACK_MODEL:
                try:
                    logger.info(f"[VisionEngine] Attempting fallback to {settings.FALLBACK_MODEL}...")
                    self.model = YOLO(settings.FALLBACK_MODEL)
                    self.active_model_path = settings.FALLBACK_MODEL
                    logger.info("[VisionEngine] Fallback model loaded successfully.")
                except Exception as ex:
                    logger.critical(f"[VisionEngine] CRITICAL: Fallback model loading failed: {ex}")
                    self.model = None

    def detect(self, image_bytes: bytes) -> Tuple[Dict[str, Any], bytes]:
        """
        Executes inference on raw JPEG bytes.
        Returns:
            summary_dict: dictionary containing structured telemetry, bboxes, and counts
            annotated_jpeg_bytes: image with rendered bounding boxes & confidence badges
        """
        start_time = time.time()
        self.total_inferences += 1
        
        # Decode raw JPEG bytes into OpenCV BGR numpy array
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Corrupt image data: OpenCV failed to decode frame.")

        height, width, _ = img.shape
        detections: List[Dict[str, Any]] = []
        counts: Dict[str, int] = {}
        annotated_img = img.copy()

        if self.model is not None:
            # Ultralytics inference call
            results = self.model.predict(
                source=img,
                conf=settings.CONFIDENCE_THRESHOLD,
                device=settings.DEVICE,
                verbose=False
            )

            result = results[0]
            names = result.names

            for box in result.boxes:
                coords = box.xyxy[0].tolist()  # [x1, y1, x2, y2]
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                class_name = names.get(cls_id, f"item_{cls_id}")

                x1, y1, x2, y2 = coords
                # Calculate normalized coordinates (0.0 to 1.0) for responsive frontend canvas
                norm_box = [
                    round(x1 / width, 4),
                    round(y1 / height, 4),
                    round(x2 / width, 4),
                    round(y2 / height, 4)
                ]

                detections.append({
                    "class_name": class_name,
                    "confidence": round(conf, 3),
                    "box": [round(c, 1) for c in coords],
                    "normalized_box": norm_box
                })

                counts[class_name] = counts.get(class_name, 0) + 1

                # Render bounding box on annotated image
                ix1, iy1, ix2, iy2 = int(x1), int(y1), int(x2), int(y2)
                cv2.rectangle(annotated_img, (ix1, iy1), (ix2, iy2), (34, 197, 94), 2)  # Green border
                
                # Render label badge
                label = f"{class_name} {int(conf * 100)}%"
                (w_label, h_label), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
                cv2.rectangle(annotated_img, (ix1, max(iy1 - 20, 0)), (ix1 + w_label + 8, iy1), (34, 197, 94), -1)
                cv2.putText(
                    annotated_img, label, (ix1 + 4, max(iy1 - 5, 12)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA
                )

        inference_latency_ms = round((time.time() - start_time) * 1000, 2)

        # Encode annotated image back to JPEG bytes (quality 85 for dashboard stream)
        encode_success, buffer = cv2.imencode('.jpg', annotated_img, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        annotated_bytes = buffer.tobytes() if encode_success else image_bytes

        summary = {
            "inference_latency_ms": inference_latency_ms,
            "total_detections": len(detections),
            "equipment_counts": counts,
            "detections": detections,
            "image_width": width,
            "image_height": height
        }

        return summary, annotated_bytes

# Global singleton instance
detector = VisionDetector()
