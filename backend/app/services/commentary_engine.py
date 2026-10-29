import time
import math
import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
import httpx

from app.config import settings

logger = logging.getLogger("uvicorn.error")

PORTABLE_ITEMS = {
    "bottle", "cup", "cell_phone", "mouse", "keyboard", "book", "remote",
    "microcontroller", "wine glass", "bowl", "apple", "sandwich"
}

def box_distance(box1: List[float], box2: List[float]) -> float:
    """Calculates Euclidean distance between centers of two boxes."""
    c1x = (box1[0] + box1[2]) / 2.0
    c1y = (box1[1] + box1[3]) / 2.0
    c2x = (box2[0] + box2[2]) / 2.0
    c2y = (box2[1] + box2[3]) / 2.0
    return math.hypot(c1x - c2x, c1y - c2y)

def box_overlap(box1: List[float], box2: List[float]) -> bool:
    """Checks if box1 intersects or touches box2."""
    return not (box1[2] < box2[0] or box1[0] > box2[2] or box1[3] < box2[1] or box1[1] > box2[3])

def get_spatial_region(norm_box: List[float]) -> str:
    if not norm_box or len(norm_box) != 4:
        return "in the scene"
    cx = (norm_box[0] + norm_box[2]) / 2.0
    cy = (norm_box[1] + norm_box[3]) / 2.0
    
    # Check depth / scale: small height often indicates background
    h = norm_box[3] - norm_box[1]
    is_background = h < 0.40 and cy < 0.60

    h_desc = "on the left" if cx < 0.35 else ("on the right" if cx > 0.65 else "in the center")
    if is_background:
        return f"in the background {h_desc}"
    return h_desc


class CommentaryEngine:
    """
    Real-Time AI Scene Commentator
    Analyzes temporal object interactions (e.g. picking up bottles, walking into frame, moving tools)
    and uses local SLM (Qwen 2.5 1.5B via Ollama) to generate live broadcast narration.
    """
    def __init__(self):
        self.last_detections: List[Dict[str, Any]] = []
        self.last_commentary: Optional[Dict[str, Any]] = None
        self.last_commentary_time: float = 0.0
        self.min_interval_seconds: float = 3.5  # Prevent commentary spamming
        self.is_busy: bool = False
        self.commentary_history: List[Dict[str, Any]] = []
        self.history_max_len: int = 25

    def detect_action_event(self, current_detections: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Analyzes delta between last frame and current frame to detect human actions
        such as picking up an object, setting down an item, or moving into view.
        """
        now = time.time()
        if now - self.last_commentary_time < self.min_interval_seconds:
            return None

        if not self.last_detections and not current_detections:
            return None

        # Build current & previous class maps
        prev_by_class: Dict[str, List[Dict[str, Any]]] = {}
        for d in self.last_detections:
            prev_by_class.setdefault(d["class_name"], []).append(d)

        curr_by_class: Dict[str, List[Dict[str, Any]]] = {}
        for d in current_detections:
            curr_by_class.setdefault(d["class_name"], []).append(d)

        prev_persons = prev_by_class.get("person", [])
        curr_persons = curr_by_class.get("person", [])

        # 1. ACTION: Person entered or left
        if len(curr_persons) > len(prev_persons):
            p = curr_persons[0]
            region = get_spatial_region(p.get("normalized_box", []))
            return {
                "event_type": "person_entered",
                "target": "person",
                "region": region,
                "description": f"A person walked into view {region}"
            }
        elif len(curr_persons) < len(prev_persons) and len(prev_persons) > 0:
            return {
                "event_type": "person_left",
                "target": "person",
                "region": "out of frame",
                "description": "A person stepped out of the camera frame"
            }

        # 2. ACTION: Interaction between Person and Portable Item (e.g. bottle, cup, phone, microcontroller)
        if curr_persons:
            person = curr_persons[0]
            p_box = person["box"]

            for item_name in PORTABLE_ITEMS:
                prev_items = prev_by_class.get(item_name, [])
                curr_items = curr_by_class.get(item_name, [])

                # Case A: Item was present near person in previous frame, now missing or picked up
                if len(prev_items) > len(curr_items):
                    # Check if the missing item was close to the person
                    missing = prev_items[0]
                    if box_overlap(p_box, missing["box"]) or box_distance(p_box, missing["box"]) < 180:
                        region = get_spatial_region(missing.get("normalized_box", []))
                        return {
                            "event_type": "picked_up",
                            "target": item_name.replace('_', ' '),
                            "region": region,
                            "description": f"A person just picked up a {item_name.replace('_', ' ')} {region}"
                        }

                # Case B: Item suddenly appeared near person (set down)
                if len(curr_items) > len(prev_items):
                    new_item = curr_items[0]
                    if box_overlap(p_box, new_item["box"]) or box_distance(p_box, new_item["box"]) < 180:
                        region = get_spatial_region(new_item.get("normalized_box", []))
                        return {
                            "event_type": "placed_down",
                            "target": item_name.replace('_', ' '),
                            "region": region,
                            "description": f"A person set down a {item_name.replace('_', ' ')} {region}"
                        }

                # Case C: Item moved significantly while near person (e.g. taking a sip or carrying)
                if prev_items and curr_items:
                    old_box = prev_items[0]["box"]
                    new_box = curr_items[0]["box"]
                    dist = box_distance(old_box, new_box)
                    if dist > 65 and (box_overlap(p_box, new_box) or box_distance(p_box, new_box) < 180):
                        region = get_spatial_region(curr_items[0].get("normalized_box", []))
                        return {
                            "event_type": "moved_item",
                            "target": item_name.replace('_', ' '),
                            "region": region,
                            "description": f"Someone is handling or moving a {item_name.replace('_', ' ')} {region}"
                        }

        # 3. ACTION: Target equipment interaction (e.g. 3D printer, soldering station)
        if curr_persons:
            p_box = curr_persons[0]["box"]
            for target_name in ["3d_printer", "soldering_station", "oscilloscope", "dell_monitor"]:
                targets = curr_by_class.get(target_name, [])
                if targets:
                    t_box = targets[0]["box"]
                    if box_overlap(p_box, t_box) or box_distance(p_box, t_box) < 150:
                        region = get_spatial_region(targets[0].get("normalized_box", []))
                        return {
                            "event_type": "equipment_interaction",
                            "target": target_name.replace('_', ' '),
                            "region": region,
                            "description": f"An operator is working near the {target_name.replace('_', ' ')} {region}"
                        }

        return None

    async def generate_commentary_line(self, event: Dict[str, Any]) -> str:
        """
        Uses Qwen 2.5 via Ollama to generate a lively, natural broadcast commentary line.
        Falls back instantly to template formulation if Ollama is busy.
        """
        url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate"
        system_prompt = (
            "You are a witty, professional live video stream commentator for a laboratory and workspace camera. "
            "Your job is to provide a single, natural, engaging live commentary line (present tense, max 12 words) "
            "describing what just happened on camera. Do NOT use quotes, markdown or introductory words like 'Here is:'."
        )

        user_prompt = (
            f"EVENT TO DESCRIBE: {event['description']}\n"
            f"ACTION: {event['event_type']}\n"
            f"OBJECT: {event['target']}\n"
            f"LOCATION: {event['region']}\n"
            "LIVE COMMENTARY:"
        )

        payload = {
            "model": settings.OLLAMA_MODEL,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": False,
            "options": {
                "temperature": 0.4,
                "num_predict": 30
            }
        }

        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    text = res.json().get("response", "").strip()
                    # Clean any surrounding quotes
                    text = text.strip('"\'')
                    if text:
                        return text
        except Exception as e:
            logger.debug(f"[Commentary] Ollama skipped ({e}), using dynamic template.")

        # Rich template fallback
        etype = event["event_type"]
        target = event["target"]
        reg = event["region"]

        if etype == "picked_up":
            return f"Someone just picked up a {target} {reg}."
        elif etype == "placed_down":
            return f"A {target} was just placed down {reg}."
        elif etype == "person_entered":
            return f"A person has entered the scene {reg}."
        elif etype == "person_left":
            return "The person stepped out of the camera view."
        elif etype == "moved_item":
            return f"Someone is moving the {target} {reg}."
        elif etype == "equipment_interaction":
            return f"Operator is actively working near the {target}."
        
        return f"Activity observed involving {target} {reg}."

    async def process_frame_detections(self, detections: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Main entry point called on each frame.
        Detects events, generates live commentary asynchronously, and returns commentary packet.
        """
        event = self.detect_action_event(detections)
        # Update memory of previous detections for next delta
        self.last_detections = detections

        if not event or self.is_busy:
            return None

        self.is_busy = True
        self.last_commentary_time = time.time()

        try:
            commentary_text = await self.generate_commentary_line(event)
            commentary_obj = {
                "id": f"comm-{int(time.time() * 1000)}",
                "text": commentary_text,
                "action_type": event["event_type"],
                "target": event["target"],
                "region": event["region"],
                "timestamp": round(time.time(), 2),
                "model_used": settings.OLLAMA_MODEL
            }

            self.last_commentary = commentary_obj
            self.commentary_history.insert(0, commentary_obj)
            if len(self.commentary_history) > self.history_max_len:
                self.commentary_history.pop()

            return commentary_obj
        finally:
            self.is_busy = False

# Global singleton
commentary_engine = CommentaryEngine()
