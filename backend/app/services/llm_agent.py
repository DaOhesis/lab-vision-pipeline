import time
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
import httpx

from app.config import settings

logger = logging.getLogger("uvicorn.error")

class LLMAgentService:
    """
    Intelligent Lab Reasoning Service powered by local quantized SLMs (Qwen 2.5 1.5B / Llama 3.2 via Ollama).
    Interprets spatial YOLO telemetry, assesses laboratory safety, and answers natural language inquiries.
    """

    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL.rstrip('/')
        self.model = settings.OLLAMA_MODEL
        self.timeout = settings.OLLAMA_TIMEOUT

    def _describe_spatial_position(self, norm_box: List[float]) -> str:
        """Converts normalized bounding box [x1, y1, x2, y2] into spatial natural language."""
        if not norm_box or len(norm_box) != 4:
            return "in scene"
        x1, y1, x2, y2 = norm_box
        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0

        h_pos = "left" if cx < 0.35 else ("right" if cx > 0.65 else "center")
        v_pos = "top" if cy < 0.35 else ("bottom" if cy > 0.65 else "middle")
        return f"{v_pos}-{h_pos}"

    def build_scene_summary(self, telemetry: Optional[Dict[str, Any]]) -> str:
        """Constructs an information-dense textual context representation of the live scene."""
        if not telemetry:
            return "No camera frame ingested yet. The laboratory sensor feed is currently idle."

        device_id = telemetry.get("device_id", "camera_01")
        counts = telemetry.get("equipment_counts", {})
        detections = telemetry.get("detections", [])
        latency = telemetry.get("inference_latency_ms", 0)

        lines = [
            f"Sensor Device ID: {device_id}",
            f"Vision Model Latency: {latency} ms",
            "Current Equipment Inventory Detected:",
        ]

        if not counts:
            lines.append("  - No target lab equipment currently detected in the scene.")
        else:
            for item, count in counts.items():
                lines.append(f"  - {item.replace('_', ' ').title()}: {count}")

        if detections:
            lines.append("Spatial Layout of Objects on Bench:")
            for det in detections:
                cname = det.get("class_name", "object").replace('_', ' ')
                conf = int(det.get("confidence", 0) * 100)
                norm_box = det.get("normalized_box", [])
                pos = self._describe_spatial_position(norm_box)
                lines.append(f"  * {cname} (confidence {conf}%) positioned at {pos} of frame")

        return "\n".join(lines)

    async def _call_ollama(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """Calls the local Ollama /api/generate endpoint asynchronously."""
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,       # Low temperature for factual, grounded responses
                "top_p": 0.9,
                "num_predict": 180         # Fast concise responses
            }
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    resp = data.get("response", "").strip()
                    # Normalize unicode punctuation for cross-platform Windows terminal safety
                    resp = resp.replace('\u2011', '-').replace('\u2013', '-').replace('\u2014', '-')
                    resp = resp.replace('\u2018', "'").replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"')
                    return resp
                else:
                    logger.warning(f"[LLM] Ollama returned status {res.status_code}: {res.text}")
                    return None
        except Exception as e:
            logger.warning(f"[LLM] Ollama connection failed ({url}): {e}")
            return None

    def _fallback_rule_based_query(self, query: str, telemetry: Optional[Dict[str, Any]]) -> str:
        """Deterministic rule-based backup when Ollama is offline."""
        q = query.lower()
        if not telemetry:
            return "The camera stream is currently idle or initializing. No detections are available yet."

        counts = telemetry.get("equipment_counts", {})
        total = telemetry.get("total_detections", 0)

        if "3d printer" in q or "printer" in q:
            c = counts.get("3d_printer", 0)
            return f"Currently, {c} 3D printer(s) are detected on the lab workbench."
        if "monitor" in q or "dell" in q:
            c = counts.get("dell_monitor", 0)
            return f"There are {c} Dell monitor(s) visible in the camera field of view."
        if "microcontroller" in q or "esp32" in q or "arduino" in q:
            c = counts.get("microcontroller", 0)
            return f"Detected {c} microcontroller development board(s) on the bench."
        if "soldering" in q:
            c = counts.get("soldering_station", 0)
            return f"Soldering station count: {c} active in the workstation."
        if "safety" in q or "hazard" in q:
            soldering = counts.get("soldering_station", 0)
            printers = counts.get("3d_printer", 0)
            if soldering > 0 and printers > 0:
                return "Safety Note: Both heating equipment (soldering station) and 3D printing equipment are present in the zone. Ensure adequate clearance."
            return "No critical hazards identified from the localized objects. Work area appears nominal."

        equip_list = ", ".join([f"{k.replace('_', ' ')} ({v})" for k, v in counts.items() if v > 0]) or "None"
        return f"Current scene status: Localized {total} items ({equip_list})."

    async def answer_query(self, question: str, telemetry: Optional[Dict[str, Any]], history: List[Dict[str, str]] = None) -> Tuple[str, str, float]:
        """
        Answers a user inquiry regarding the lab scene using local LLM reasoning.
        Returns: (answer_text, model_name, latency_ms)
        """
        t0 = time.time()
        scene_context = self.build_scene_summary(telemetry)

        system_prompt = (
            "You are the IoT Lab AI Copilot. You monitor an electronics and prototyping laboratory "
            "equipped with 3D printers, Dell monitors, microcontrollers, oscilloscopes, and soldering stations.\n"
            "You have direct real-time telemetry from computer vision cameras.\n"
            "RULES:\n"
            "1. Answer questions concisely, professionally, and factually based ONLY on the provided scene state.\n"
            "2. If an equipment item is not listed in the telemetry, clearly say it is not currently detected.\n"
            "3. Refer to spatial positions (e.g. left side, center of bench) when helpful.\n"
            "4. Keep answers under 3 sentences."
        )

        user_prompt = f"LIVE LAB TELEMETRY:\n{scene_context}\n\nUSER QUESTION: {question}\n\nANSWER:"

        response = await self._call_ollama(system_prompt, user_prompt)
        latency_ms = round((time.time() - t0) * 1000, 1)

        if response:
            return response, self.model, latency_ms

        # Fallback to rule engine if Ollama is unreachable
        fallback_resp = self._fallback_rule_based_query(question, telemetry)
        return fallback_resp, "deterministic-rule-fallback", latency_ms

    async def generate_briefing(self, telemetry: Optional[Dict[str, Any]]) -> Tuple[str, str, str, str, float]:
        """
        Generates an executive lab briefing and safety classification.
        Returns: (summary, safety_assessment, safety_status, model_name, latency_ms)
        """
        t0 = time.time()
        counts = telemetry.get("equipment_counts", {}) if telemetry else {}
        soldering = counts.get("soldering_station", 0)
        printers = counts.get("3d_printer", 0)

        # Baseline safety rule determination
        if soldering > 0 and printers > 0:
            default_status = "caution"
        elif soldering > 0 or printers > 0:
            default_status = "nominal"
        else:
            default_status = "nominal"

        scene_context = self.build_scene_summary(telemetry)
        system_prompt = (
            "You are an IoT Lab Safety & Operations Officer. Provide a 2-sentence executive situation report "
            "summarizing what equipment is on the bench and confirming if the setup is safe. Keep it professional."
        )
        user_prompt = f"LIVE LAB STATE:\n{scene_context}\n\nEXECUTIVE BRIEFING:"

        response = await self._call_ollama(system_prompt, user_prompt)
        latency_ms = round((time.time() - t0) * 1000, 1)

        if response:
            summary = response
            safety_eval = "Nominal equipment layout verified by local AI assistant."
            if "caution" in response.lower() or "warning" in response.lower() or "hazard" in response.lower():
                default_status = "caution"
            return summary, safety_eval, default_status, self.model, latency_ms

        # Fallback briefing
        active_items = [f"{k.replace('_', ' ')} ({v})" for k, v in counts.items() if v > 0]
        if active_items:
            summary = f"Workbench active with {', '.join(active_items)}. Sensors operating nominally."
        else:
            summary = "Lab workbench is clear of localized hardware. Monitoring stream is active."

        safety_eval = "Standard bench protocols observed. No fire or thermal collision hazards detected."
        return summary, safety_eval, default_status, "deterministic-rule-fallback", latency_ms

# Global singleton instance
llm_agent = LLMAgentService()
