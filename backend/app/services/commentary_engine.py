import time
import math
import logging
from typing import List, Dict, Any, Optional, Tuple
import httpx

from app.config import settings

logger = logging.getLogger("uvicorn.error")

PORTABLE_ITEMS = {
    "bottle", "cup", "cell_phone", "phone", "mouse", "keyboard", "book", "remote",
    "microcontroller", "wine glass", "bowl", "apple", "sandwich"
}

def box_center(box: List[float]) -> Tuple[float, float]:
    """Calculates normalized center (cx, cy) from [x1, y1, x2, y2]."""
    return ((box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0)

def box_distance(box1: List[float], box2: List[float]) -> float:
    """Calculates Euclidean distance between centers of two normalized boxes."""
    c1 = box_center(box1)
    c2 = box_center(box2)
    return math.hypot(c1[0] - c2[0], c1[1] - c2[1])

def box_overlap(box1: List[float], box2: List[float]) -> bool:
    """Checks if box1 intersects box2."""
    return not (box1[2] < box2[0] or box1[0] > box2[2] or box1[3] < box2[1] or box1[1] > box2[3])

def get_spatial_region(norm_box: List[float]) -> str:
    if not norm_box or len(norm_box) != 4:
        return "in the scene"
    cx = (norm_box[0] + norm_box[2]) / 2.0
    cy = (norm_box[1] + norm_box[3]) / 2.0
    
    h_desc = "on the left" if cx < 0.35 else ("on the right" if cx > 0.65 else "in the center")
    return h_desc


class CommentaryEngine:
    """
    Real-Time AI Scene Commentary & Behavioral Narrator.
    Generates intelligent live broadcast commentary when:
      - Two or more people are talking / interacting in close proximity
      - Someone moves away or leaves the camera view
      - Someone enters or joins the frame
      - A person uses a phone or works on a laptop
      - Objects are handled, picked up, or relocated
    """

    def __init__(self):
        self.last_detections: List[Dict[str, Any]] = []
        self.last_commentary: Optional[Dict[str, Any]] = None
        self.last_commentary_time: float = 0.0
        self.min_interval_seconds: float = 3.0  # Cooldown between rapid events
        self.last_activity_type: str = "initial"
        self.last_people_count: int = -1
        self.last_person_positions: List[Tuple[float, float]] = []
        self.is_busy: bool = False
        self.commentary_history: List[Dict[str, Any]] = []
        self.history_max_len: int = 30
        self.cooldown_by_type: Dict[str, float] = {}

    def _is_rate_limited(self, event_type: str, cooldown: float = 5.0) -> bool:
        now = time.time()
        last_time = self.cooldown_by_type.get(event_type, 0.0)
        if now - last_time < cooldown:
            return True
        return False

    def _mark_triggered(self, event_type: str):
        self.cooldown_by_type[event_type] = time.time()
        self.last_commentary_time = time.time()
        self.last_activity_type = event_type

    def detect_action_event(self, current_detections: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Analyzes scene dynamics and returns an event payload when a meaningful action occurs.
        """
        now = time.time()

        # Group current detections by category
        people = [d for d in current_detections if d.get("class_name") == "person"]
        phones = [d for d in current_detections if "phone" in d.get("class_name", "")]
        laptops = [d for d in current_detections if "laptop" in d.get("class_name", "") or "monitor" in d.get("class_name", "")]
        cups = [d for d in current_detections if d.get("class_name") in ["cup", "bottle"]]

        curr_people_count = len(people)
        prev_people_count = self.last_people_count if self.last_people_count != -1 else curr_people_count

        # ------------------------------------------------------------------
        # 1. MOVEMENT / TRANSITIONS: Someone moved away or entered
        # ------------------------------------------------------------------
        if curr_people_count < prev_people_count and not self._is_rate_limited("person_left", 3.0):
            self.last_people_count = curr_people_count
            if curr_people_count == 0:
                self._mark_triggered("person_left")
                return {
                    "event_type": "person_left",
                    "target": "person",
                    "region": "out of frame",
                    "description": "The person has moved away and left the camera view."
                }
            else:
                diff = prev_people_count - curr_people_count
                self._mark_triggered("person_left")
                return {
                    "event_type": "person_left",
                    "target": "person",
                    "region": "out of frame",
                    "description": f"Someone moved away ({curr_people_count} person remaining in view)."
                }

        if curr_people_count > prev_people_count and not self._is_rate_limited("person_entered", 3.0):
            self.last_people_count = curr_people_count
            self._mark_triggered("person_entered")
            if prev_people_count == 0:
                return {
                    "event_type": "person_entered",
                    "target": "person",
                    "region": get_spatial_region(people[0].get("normalized_box", [])),
                    "description": "A person has walked into the scene."
                }
            else:
                return {
                    "event_type": "person_entered",
                    "target": "person",
                    "region": "into frame",
                    "description": "Another person has joined the camera view."
                }

        self.last_people_count = curr_people_count

        # ------------------------------------------------------------------
        # 2. SOCIAL INTERACTION: Two or more people talking / conversing
        # ------------------------------------------------------------------
        if curr_people_count >= 2:
            # Find proximity between the two closest people
            min_dist = 999.0
            p1_box, p2_box = people[0].get("normalized_box", []), people[1].get("normalized_box", [])
            for i in range(len(people)):
                for j in range(i + 1, len(people)):
                    b1 = people[i].get("normalized_box", [])
                    b2 = people[j].get("normalized_box", [])
                    d = box_distance(b1, b2)
                    if d < min_dist:
                        min_dist = d
                        p1_box, p2_box = b1, b2

            # Close conversational distance: normalized distance < 0.42
            if min_dist < 0.42 and not self._is_rate_limited("people_talking", 6.0):
                reg = get_spatial_region(p1_box)
                self._mark_triggered("people_talking")
                if curr_people_count == 2:
                    return {
                        "event_type": "people_talking",
                        "target": "two people",
                        "region": reg,
                        "description": f"Two people are standing close together and engaged in conversation {reg}."
                    }
                else:
                    return {
                        "event_type": "people_talking",
                        "target": "group",
                        "region": reg,
                        "description": f"A group of {curr_people_count} people have gathered and are talking {reg}."
                    }

        # ------------------------------------------------------------------
        # 3. POSITION SHIFT: Person moved across the frame
        # ------------------------------------------------------------------
        if curr_people_count == 1 and self.last_person_positions:
            curr_pos = box_center(people[0].get("normalized_box", [0, 0, 0, 0]))
            prev_pos = self.last_person_positions[0]
            # Check significant horizontal movement (> 0.28 normalized width)
            if abs(curr_pos[0] - prev_pos[0]) > 0.28 and not self._is_rate_limited("person_moved", 5.0):
                new_reg = "to the left" if curr_pos[0] < prev_pos[0] else "to the right"
                self._mark_triggered("person_moved")
                self.last_person_positions = [curr_pos]
                return {
                    "event_type": "person_moved",
                    "target": "person",
                    "region": new_reg,
                    "description": f"The person shifted position and moved {new_reg}."
                }
            self.last_person_positions = [curr_pos]
        elif curr_people_count == 1:
            self.last_person_positions = [box_center(people[0].get("normalized_box", [0, 0, 0, 0]))]

        # ------------------------------------------------------------------
        # 4. OBJECT & DEVICE INTERACTIONS: Phone or Laptop usage
        # ------------------------------------------------------------------
        if curr_people_count == 1:
            pbox = people[0].get("normalized_box", [])

            # Phone usage
            if phones and not self._is_rate_limited("using_phone", 7.0):
                ph_box = phones[0].get("normalized_box", [])
                if box_overlap(pbox, ph_box) or box_distance(pbox, ph_box) < 0.25:
                    self._mark_triggered("using_phone")
                    return {
                        "event_type": "using_phone",
                        "target": "mobile phone",
                        "region": "in hand",
                        "description": "The person is holding and using a mobile phone."
                    }

            # Laptop / workstation activity
            if laptops and not self._is_rate_limited("working_laptop", 8.0):
                l_box = laptops[0].get("normalized_box", [])
                if box_overlap(pbox, l_box) or box_distance(pbox, l_box) < 0.35:
                    self._mark_triggered("working_laptop")
                    return {
                        "event_type": "working_laptop",
                        "target": "laptop",
                        "region": "at desk",
                        "description": "The person is seated and actively working on the computer."
                    }

            # Drink interaction
            if cups and not self._is_rate_limited("drinking", 8.0):
                c_box = cups[0].get("normalized_box", [])
                if box_overlap(pbox, c_box) or box_distance(pbox, c_box) < 0.22:
                    self._mark_triggered("drinking")
                    return {
                        "event_type": "drinking",
                        "target": "drink",
                        "region": "at desk",
                        "description": "The person is reaching for or handling a drink."
                    }

        # ------------------------------------------------------------------
        # 5. PERIODIC AMBIENT REFRESH (Every 10-12s if nothing new changed)
        # ------------------------------------------------------------------
        if now - self.last_commentary_time > 12.0:
            if curr_people_count == 1:
                reg = get_spatial_region(people[0].get("normalized_box", []))
                self._mark_triggered("ambient_occupied")
                return {
                    "event_type": "ambient_occupied",
                    "target": "person",
                    "region": reg,
                    "description": f"A person is currently present {reg} of the camera view."
                }
            elif curr_people_count == 0:
                self._mark_triggered("ambient_unoccupied")
                return {
                    "event_type": "ambient_unoccupied",
                    "target": "workspace",
                    "region": "entire scene",
                    "description": "The scene is currently quiet and unoccupied."
                }

        return None

    async def generate_commentary_line(self, event: Dict[str, Any]) -> str:
        """
        Uses local SLM (Qwen 2.5 via Ollama) if available for lively commentary,
        otherwise returns dynamic high-quality template output immediately.
        """
        # If Ollama is enabled, attempt concise AI commentary
        if settings.OLLAMA_BASE_URL:
            url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate"
            system_prompt = (
                "You are an engaging, witty live video commentator narrating what people are doing on camera. "
                "Provide a single natural, lively commentary sentence (present tense, max 14 words). "
                "Do NOT use quotes or meta-commentary."
            )
            user_prompt = f"OBSERVATION: {event['description']}\nCOMMENTARY:"

            try:
                async with httpx.AsyncClient(timeout=2.0) as client:
                    res = await client.post(url, json={
                        "model": settings.OLLAMA_MODEL,
                        "system": system_prompt,
                        "prompt": user_prompt,
                        "stream": False,
                        "options": {"temperature": 0.4, "num_predict": 25}
                    })
                    if res.status_code == 200:
                        text = res.json().get("response", "").strip().strip('"\'')
                        text = text.replace('\u2011', '-').replace('\u2013', '-').replace('\u2014', '-')
                        text = text.replace('\u2018', "'").replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"')
                        text = text.replace('\u2026', '...').replace('\u00a0', ' ')
                        cleaned = text.encode('ascii', errors='ignore').decode('ascii').strip()
                        if cleaned:
                            return cleaned
            except Exception:
                pass

        # Dynamic instant template fallback (< 0.1ms)
        return event["description"]

    async def process_frame_detections(self, detections: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Called on each frame. Detects events and returns a commentary packet if a new event fired.
        """
        event = self.detect_action_event(detections)
        self.last_detections = detections

        if not event or self.is_busy:
            return None

        self.is_busy = True
        try:
            commentary_text = await self.generate_commentary_line(event)
            commentary_obj = {
                "id": f"comm-{int(time.time() * 1000)}",
                "text": commentary_text,
                "action_type": event["event_type"],
                "target": event["target"],
                "region": event["region"],
                "timestamp": round(time.time(), 2),
                "time_str": time.strftime("%H:%M:%S")
            }

            self.last_commentary = commentary_obj
            self.commentary_history.insert(0, commentary_obj)
            if len(self.commentary_history) > self.history_max_len:
                self.commentary_history.pop()

            return commentary_obj
        finally:
            self.is_busy = False


# Global singleton instance
commentary_engine = CommentaryEngine()
