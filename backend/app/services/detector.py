import os
import time
import logging
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
import cv2
from ultralytics import YOLO

from app.config import settings

logger = logging.getLogger("uvicorn.error")

# Exotic / unlikely indoor desktop classes that small models occasionally hallucinate on low confidence:
SUSPICIOUS_EXOTIC_CLASSES = {
    "airplane", "boat", "train", "traffic light", "fire hydrant", "stop sign", "parking meter",
    "bird", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe",
    "frisbee", "skis", "snowboard", "baseball glove", "surfboard", "tennis racket",
    "toilet", "sink", "toothbrush", "bench", "kite"
}

# Human-friendly aliases for standard tech & desk objects
CLASS_ALIAS_MAP = {
    "tv": "monitor",
    "dining table": "desk",
    "potted plant": "plant",
    "cell phone": "cell_phone",
}

# Mapping common desk equipment to IoT lab categories when using base pretrained weights
LAB_TAXONOMY_MAP = {
    "monitor": "dell_monitor",
    "tv": "dell_monitor",
    "remote": "microcontroller",
}


def calculate_iou(boxA: List[float], boxB: List[float]) -> float:
    """Calculates Intersection over Union (IoU) between two [x1, y1, x2, y2] bounding boxes."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    interArea = max(0.0, xB - xA) * max(0.0, yB - yA)
    boxAArea = max(0.0, boxA[2] - boxA[0]) * max(0.0, boxA[3] - boxA[1])
    boxBArea = max(0.0, boxB[2] - boxB[0]) * max(0.0, boxB[3] - boxB[1])

    denom = boxAArea + boxBArea - interArea
    return interArea / denom if denom > 0 else 0.0


class TrackedItem:
    def __init__(self, class_name: str, box: List[float], confidence: float):
        self.class_name = class_name
        self.box = box
        self.confidence = confidence
        self.hits = 1
        self.misses = 0

    def update(self, new_box: List[float], new_conf: float, alpha: float):
        # Exponential moving average for smooth bounding box gliding without jitter
        self.box = [
            round(alpha * nb + (1.0 - alpha) * ob, 2)
            for nb, ob in zip(new_box, self.box)
        ]
        self.confidence = round(0.7 * new_conf + 0.3 * self.confidence, 3)
        self.hits += 1
        self.misses = 0


class TemporalTracker:
    """
    Multi-frame IoU tracker that smooths bounding box jitter and filters out
    1-frame transient hallucinations and false positives in real-time video streams.
    """
    def __init__(self, alpha: float = 0.70, max_missed: int = 2, min_hits: int = 2):
        self.alpha = alpha
        self.max_missed = max_missed
        self.min_hits = min_hits
        self.tracked_items: List[TrackedItem] = []

    def update(self, raw_detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        matched_tracked = set()
        matched_raw = set()

        # Match new detections with existing tracked items based on IoU and class compatibility
        for r_idx, raw in enumerate(raw_detections):
            best_iou = 0.0
            best_t_idx = -1

            for t_idx, tracked in enumerate(self.tracked_items):
                if t_idx in matched_tracked:
                    continue
                if tracked.class_name != raw["class_name"]:
                    continue

                iou = calculate_iou(raw["box"], tracked.box)
                if iou > best_iou:
                    best_iou = iou
                    best_t_idx = t_idx

            if best_iou >= 0.40 and best_t_idx >= 0:
                self.tracked_items[best_t_idx].update(raw["box"], raw["confidence"], self.alpha)
                matched_tracked.add(best_t_idx)
                matched_raw.add(r_idx)

        # Increment misses for unmatched tracked items
        for t_idx, tracked in enumerate(self.tracked_items):
            if t_idx not in matched_tracked:
                tracked.misses += 1

        # Remove dead tracks
        self.tracked_items = [
            t for t in self.tracked_items if t.misses <= self.max_missed
        ]

        # Add new unmatched raw detections
        for r_idx, raw in enumerate(raw_detections):
            if r_idx not in matched_raw:
                new_track = TrackedItem(raw["class_name"], raw["box"], raw["confidence"])
                self.tracked_items.append(new_track)

        # Filter confirmed detections:
        # High confidence (>=0.55) appears immediately; lower confidence requires 2 frames to prevent noise
        confirmed = []
        for t in self.tracked_items:
            if t.hits >= self.min_hits or t.confidence >= 0.55:
                confirmed.append({
                    "class_name": t.class_name,
                    "confidence": t.confidence,
                    "box": t.box,
                    "is_active": t.misses == 0
                })

        return confirmed


class VisionDetector:
    """
    Advanced YOLO Inference Engine with state-of-the-art YOLO11 backbone,
    Class-Agnostic NMS, domain false-positive filtering, and temporal bounding box smoothing.
    """
    def __init__(self):
        self.model: Optional[YOLO] = None
        self.active_model_path: str = ""
        self.total_inferences: int = 0
        self.confidence_threshold: float = settings.CONFIDENCE_THRESHOLD
        self.iou_threshold: float = settings.IOU_THRESHOLD
        self.tracker = TemporalTracker(
            alpha=settings.TRACKER_SMOOTHING_ALPHA,
            max_missed=settings.TRACKER_MAX_MISSED_FRAMES,
            min_hits=settings.MIN_CONSECUTIVE_FRAMES
        )
        self._initialize_model()

    def _resolve_model_path(self, target: Optional[str] = None) -> str:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        
        candidates = []
        if target:
            candidates.extend([
                target,
                os.path.join(project_root, target),
                os.path.join(backend_dir, target),
                os.path.join(project_root, "models", target),
                os.path.join(backend_dir, "models", target),
            ])
        
        preferred = [
            settings.MODEL_PATH,
            settings.FALLBACK_MODEL,
            "models/yolo11s.pt",
            "models/yolo11m.pt",
            "models/yolo11n.pt",
            "yolo11s.pt",
            "yolo11n.pt"
        ]
        for item in preferred:
            candidates.extend([
                item,
                os.path.join(project_root, item),
                os.path.join(backend_dir, item)
            ])

        for p in candidates:
            if p and os.path.exists(p) and not os.path.isdir(p):
                return os.path.abspath(p)
                
        return "yolo11s.pt"

    def _initialize_model(self, target_path: Optional[str] = None):
        chosen_path = self._resolve_model_path(target_path)
        logger.info(f"[VisionEngine] Initializing YOLO model from: {chosen_path} (Target device: {settings.DEVICE})")
        
        try:
            self.model = YOLO(chosen_path)
            self.active_model_path = chosen_path
            logger.info(f"[VisionEngine] Model successfully loaded into memory: {chosen_path}")
        except Exception as e:
            logger.error(f"[VisionEngine] Error loading model from {chosen_path}: {e}")
            try:
                fallback = "yolo11s.pt"
                logger.info(f"[VisionEngine] Attempting fallback to {fallback}...")
                self.model = YOLO(fallback)
                self.active_model_path = fallback
                logger.info("[VisionEngine] Fallback model loaded successfully.")
            except Exception as ex:
                logger.critical(f"[VisionEngine] CRITICAL: Fallback model loading failed: {ex}")
                self.model = None

    def switch_model(self, model_name: str) -> bool:
        """Dynamically switches active YOLO model weights at runtime."""
        path = self._resolve_model_path(model_name)
        try:
            self.model = YOLO(path)
            self.active_model_path = path
            self.tracker = TemporalTracker(
                alpha=settings.TRACKER_SMOOTHING_ALPHA,
                max_missed=settings.TRACKER_MAX_MISSED_FRAMES,
                min_hits=settings.MIN_CONSECUTIVE_FRAMES
            )
            logger.info(f"[VisionEngine] Switched active model to: {path}")
            return True
        except Exception as e:
            logger.error(f"[VisionEngine] Failed to switch to model {model_name}: {e}")
            return False

    def detect(self, image_bytes: bytes) -> Tuple[Dict[str, Any], bytes]:
        """
        Executes high-accuracy inference with Agnostic NMS, domain filtering,
        temporal smoothing, and inventory telemetry tallying.
        """
        start_time = time.time()
        self.total_inferences += 1
        
        # Decode raw JPEG bytes into OpenCV BGR numpy array
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Corrupt image data: OpenCV failed to decode frame.")

        height, width, _ = img.shape
        raw_detections: List[Dict[str, Any]] = []

        if self.model is not None:
            # Ultralytics inference call with Agnostic NMS to remove conflicting multi-class boxes
            results = self.model.predict(
                source=img,
                conf=self.confidence_threshold,
                iou=self.iou_threshold,
                agnostic_nms=settings.AGNOSTIC_NMS,
                imgsz=640,
                device=settings.DEVICE,
                verbose=False
            )

            result = results[0]
            names = result.names

            for box in result.boxes:
                coords = box.xyxy[0].tolist()  # [x1, y1, x2, y2]
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                raw_class_name = names.get(cls_id, f"item_{cls_id}").strip().lower()

                # Domain filter: suppress bizarre exotic hallucinations (e.g. toilet, bird, airplane) in indoor desk
                if raw_class_name in SUSPICIOUS_EXOTIC_CLASSES and conf < 0.70:
                    continue

                # Normalize class name to human-friendly terms
                class_name = CLASS_ALIAS_MAP.get(raw_class_name, raw_class_name)

                # Clamp bounding box coordinates strictly inside image boundaries
                x1 = max(0.0, min(float(width), coords[0]))
                y1 = max(0.0, min(float(height), coords[1]))
                x2 = max(0.0, min(float(width), coords[2]))
                y2 = max(0.0, min(float(height), coords[3]))

                # Reject degenerate or tiny bounding boxes (< 15px)
                if (x2 - x1) < 15 or (y2 - y1) < 15:
                    continue

                raw_detections.append({
                    "class_name": class_name,
                    "confidence": round(conf, 3),
                    "box": [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)]
                })

        # Apply multi-frame temporal smoothing if enabled
        if settings.ENABLE_TRACKER:
            smoothed = self.tracker.update(raw_detections)
        else:
            smoothed = raw_detections

        final_detections: List[Dict[str, Any]] = []
        counts: Dict[str, int] = {}
        annotated_img = img.copy()

        for det in smoothed:
            class_name = det["class_name"]
            conf = det["confidence"]
            x1, y1, x2, y2 = det["box"]

            norm_box = [
                round(x1 / width, 4),
                round(y1 / height, 4),
                round(x2 / width, 4),
                round(y2 / height, 4)
            ]

            final_detections.append({
                "class_name": class_name,
                "confidence": conf,
                "box": [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)],
                "normalized_box": norm_box
            })

            # Tally counts for both direct class name and mapped lab equipment
            counts[class_name] = counts.get(class_name, 0) + 1
            lab_key = LAB_TAXONOMY_MAP.get(class_name)
            if lab_key:
                counts[lab_key] = counts.get(lab_key, 0) + 1

            # Render crisp bounding box on annotated server image
            ix1, iy1, ix2, iy2 = int(x1), int(y1), int(x2), int(y2)
            cv2.rectangle(annotated_img, (ix1, iy1), (ix2, iy2), (6, 182, 212), 2)  # Cyan border
            
            # Render label badge
            label = f"{class_name.capitalize()} {int(conf * 100)}%"
            (w_label, h_label), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            badge_y = max(iy1 - 20, 0)
            cv2.rectangle(annotated_img, (ix1, badge_y), (ix1 + w_label + 8, badge_y + 18), (6, 182, 212), -1)
            cv2.putText(
                annotated_img, label, (ix1 + 4, badge_y + 13),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (15, 23, 42), 1, cv2.LINE_AA
            )

        inference_latency_ms = round((time.time() - start_time) * 1000, 2)

        # Encode annotated image back to JPEG bytes (quality 85 for dashboard stream)
        encode_success, buffer = cv2.imencode('.jpg', annotated_img, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        annotated_bytes = buffer.tobytes() if encode_success else image_bytes

        summary = {
            "inference_latency_ms": inference_latency_ms,
            "total_detections": len(final_detections),
            "equipment_counts": counts,
            "detections": final_detections,
            "image_width": width,
            "image_height": height,
            "active_model": os.path.basename(self.active_model_path)
        }

        return summary, annotated_bytes

# Global singleton instance
detector = VisionDetector()
