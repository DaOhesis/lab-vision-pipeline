import time
import logging
from typing import List, Dict, Any, Optional

from app.config import settings
from app.services.llm_agent import llm_agent

logger = logging.getLogger("uvicorn.error")

CURATED_PROJECTS: List[Dict[str, Any]] = [
    {
        "id": "edge_ai_gateway",
        "title": "Edge AI Vision Gateway & Sensor Aggregator",
        "category": "Edge Computing & Telemetry",
        "difficulty": "Intermediate",
        "matched_components": ["raspberry_pi", "microcontroller"],
        "summary": "Use the Raspberry Pi as a centralized edge intelligence hub running YOLO and a local web dashboard, while the microcontroller (ESP32 / Arduino) collects real-time sensor telemetry and streams JSON packets over UART or WiFi MQTT.",
        "architecture": "ESP32 (Sensors / GPIO ADC) ---> UART Serial (115200 baud) or MQTT ---> Raspberry Pi (Local FastAPI Gateway + Next.js Dashboard)",
        "wiring_summary": "1. ESP32 TX (GPIO 17) -> RPi RX (GPIO 15 / Pin 10)\n2. ESP32 RX (GPIO 16) -> RPi TX (GPIO 14 / Pin 8)\n3. Common GND: ESP32 GND -> RPi Pin 6/9/14 (MANDATORY)\n4. Caution: Raspberry Pi GPIO is 3.3V logic. If using a 5V Arduino, use a bi-directional logic level converter.",
        "firmware_snippet": """// ESP32 Arduino / PlatformIO C++ Firmware
#include <Arduino.h>

void setup() {
  Serial.begin(115200);
  pinMode(2, OUTPUT); // Built-in Status LED
}

void loop() {
  // Read analog telemetry (e.g. ADC pin 34)
  int rawAdc = analogRead(34);
  float voltage = (rawAdc / 4095.0) * 3.3;

  // Stream structured JSON telemetry packet to Raspberry Pi
  Serial.printf("{\\"device\\":\\"microcontroller_node\\",\\"adc_v\\":%.2f,\\"raw\\":%d,\\"status\\":\\"nominal\\"}\\n", voltage, rawAdc);
  
  digitalWrite(2, HIGH);
  delay(80);
  digitalWrite(2, LOW);
  delay(920); // 1 Hz telemetry tick
}""",
        "host_snippet": """# Raspberry Pi Host Python Ingestion Script
import serial
import json
import time

# Open UART serial or USB virtual COM port
ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
print("[Raspberry Pi] Listening for microcontroller telemetry...")

while True:
    line = ser.readline().decode('utf-8', errors='ignore').strip()
    if line.startswith("{"):
        try:
            packet = json.loads(line)
            print(f"[EDGE GATEWAY] Received telemetry from node: {packet}")
            # Forward telemetry to local FastAPI vision dashboard:
            # requests.post('http://localhost:8000/api/v1/telemetry/frame', json=packet)
        except json.JSONDecodeError:
            pass
    time.sleep(0.05)""",
        "steps": [
            "1. Connect the Microcontroller to your development machine and flash the serial telemetry C++ firmware.",
            "2. Connect the Microcontroller to the Raspberry Pi using either a USB cable (easiest) or GPIO UART TX/RX with common GND.",
            "3. On the Raspberry Pi, verify the device is detected via 'ls /dev/tty*' (typically /dev/ttyUSB0 or /dev/ttyACM0).",
            "4. Install the serial communication library on the Pi: 'pip install pyserial'.",
            "5. Execute the host Python script on Raspberry Pi to ingest telemetry into your lab dashboard."
        ]
    },
    {
        "id": "pan_tilt_tracker",
        "title": "Autonomous Vision-Guided Pan-Tilt Camera Rig",
        "category": "Robotics & Computer Vision",
        "difficulty": "Advanced",
        "matched_components": ["raspberry_pi", "microcontroller"],
        "summary": "The Raspberry Pi executes local YOLO vision detection to track objects (e.g. persons, bottles, microcontrollers) and computes bounding box centroid errors. It transmits azimuth/elevation error offsets over Serial to the microcontroller, which drives 2x SG90 servo motors to center the target in frame.",
        "architecture": "Camera ---> Raspberry Pi (YOLO Centroid Offset) ---> Serial Bytes (d_pan, d_tilt) ---> ESP32 / Arduino ---> 2x SG90 Servos (PWM)",
        "wiring_summary": "1. Servo 1 (Pan): PWM Pin GPIO 18, 5V External Power, GND\n2. Servo 2 (Tilt): PWM Pin GPIO 19, 5V External Power, GND\n3. Microcontroller RX -> Raspberry Pi TX\n4. Common GND between Servos, Microcontroller, and Raspberry Pi.",
        "firmware_snippet": """// ESP32 Servo Pan-Tilt Controller
#include <ESP32Servo.h>

Servo panServo;
Servo tiltServo;
int panAngle = 90;
int tiltAngle = 90;

void setup() {
  Serial.begin(115200);
  panServo.attach(18);
  tiltServo.attach(19);
  panServo.write(panAngle);
  tiltServo.write(tiltAngle);
}

void loop() {
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\\n');
    int comma = cmd.indexOf(',');
    if (comma != -1) {
      int dPan = cmd.substring(0, comma).toInt();
      int dTilt = cmd.substring(comma + 1).toInt();
      
      panAngle = constrain(panAngle + dPan, 0, 180);
      tiltAngle = constrain(tiltAngle + dTilt, 20, 160);
      panServo.write(panAngle);
      tiltServo.write(tiltAngle);
    }
  }
}""",
        "host_snippet": """# Raspberry Pi Pan-Tilt Closed-Loop Error Transmitter
import serial

ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=0.1)

def on_yolo_detection(target_bbox, frame_width=640, frame_height=480):
    # Normalized centroid [-1.0 to 1.0]
    cx = (target_bbox[0] + target_bbox[2]) / 2.0
    cy = (target_bbox[1] + target_bbox[3]) / 2.0
    err_x = (cx - (frame_width / 2.0)) / (frame_width / 2.0)
    err_y = (cy - (frame_height / 2.0)) / (frame_height / 2.0)
    
    d_pan = int(err_x * -3) # Proportional error step
    d_tilt = int(err_y * 3)
    if abs(d_pan) > 0 or abs(d_tilt) > 0:
        ser.write(f"{d_pan},{d_tilt}\\n".encode())""",
        "steps": [
            "1. Assemble a 2-Axis mini pan-tilt bracket with two SG90 micro-servos.",
            "2. Mount the camera onto the tilt bracket.",
            "3. Power servos using an external 5V 2A power supply (do not draw servo power from Pi GPIO directly).",
            "4. Flash the closed-loop tracking firmware to the Microcontroller.",
            "5. Run the vision script on the Raspberry Pi to start autonomous tracking."
        ]
    },
    {
        "id": "standalone_lab_kiosk",
        "title": "Standalone Lab Information & Vision Kiosk",
        "category": "Lab Infrastructure",
        "difficulty": "Beginner",
        "matched_components": ["raspberry_pi", "dell_monitor"],
        "summary": "Turn your Raspberry Pi and Dell monitor into a zero-maintenance, 24/7 dedicated laboratory workstation kiosk running Chromium in full-screen mode displaying the real-time IoT Lab Vision & Telemetry dashboard.",
        "architecture": "Raspberry Pi (Local Web Engine) ---> HDMI Port ---> Dell Monitor (Full HD 1080p Kiosk)",
        "wiring_summary": "1. Connect Raspberry Pi Micro-HDMI (HDMI0) to Dell Monitor HDMI Port.\n2. Power Dell Monitor via AC wall outlet.\n3. Power Raspberry Pi with official 5.1V 3A USB-C power supply.",
        "firmware_snippet": """# Autostart configuration for Raspberry Pi OS Kiosk Mode
# File: ~/.config/wayfire.ini or /etc/xdg/lxsession/LXDE-pi/autostart
@xset s off
@xset -dpms
@xset s noblank
@chromium-browser --noerrdialogs --disable-infobars --kiosk http://localhost:3000""",
        "host_snippet": None,
        "steps": [
            "1. Connect the Raspberry Pi to the Dell monitor using an HDMI cable.",
            "2. Ensure the Next.js Lab Vision dashboard is running on port 3000.",
            "3. Launch Chromium in kiosk mode: 'chromium-browser --kiosk http://localhost:3000'.",
            "4. Configure auto-login and screen blanking disable in 'raspi-config'."
        ]
    },
    {
        "id": "custom_iot_carrier",
        "title": "Custom PCB / Breadboard Sensor Expansion Carrier",
        "category": "Electronics Prototyping",
        "difficulty": "Intermediate",
        "matched_components": ["microcontroller", "soldering_station"],
        "summary": "Use your soldering station to construct a permanent lab carrier board for your microcontroller with integrated 3.3V/5V rail filtering, I2C pullup resistors, status LEDs, and screw terminals for rugged laboratory sensor deployments.",
        "architecture": "Soldered Protoboard + Screw Terminals + Decoupling Caps + Microcontroller Socket Header",
        "wiring_summary": "1. Solder 2x female pin headers spaced for ESP32/Arduino pinout to make board swappable.\n2. Solder a 100uF electrolytic capacitor across 5V and GND rails for surge filtering.\n3. Add 4.7k ohm pull-up resistors on SDA/SCL lines for reliable I2C bus sensor communication.",
        "firmware_snippet": None,
        "host_snippet": None,
        "steps": [
            "1. Heat soldering station to 350°C and tin the soldering tip with flux-core solder.",
            "2. Insert female header sockets onto the protoboard to avoid soldering directly to the microcontroller board.",
            "3. Solder power buses, ground planes, and decoupling capacitors.",
            "4. Add 3-pin JST or screw terminal connectors for external sensors.",
            "5. Verify absence of short circuits using a multimeter in continuity mode before inserting the microcontroller."
        ]
    },
    {
        "id": "3d_printed_sensor_housing",
        "title": "Custom Weatherproof IoT Sensor Pod Enclosure",
        "category": "Additive Manufacturing",
        "difficulty": "Beginner",
        "matched_components": ["microcontroller", "3d_printer"],
        "summary": "Design and 3D print a snap-fit enclosure with ventilation grilles, mounting tabs, and transparent lens window for deploying your microcontroller sensor nodes anywhere in the laboratory or outdoors.",
        "architecture": "CAD Model (Fusion 360 / OpenSCAD) ---> Slicer (OrcaSlicer/Cura) ---> 3D Printer (PETG/PLA) ---> Snap-Fit Assembly",
        "wiring_summary": "1. Ensure internal standoffs match microcontroller mounting holes (M2.5 or M3 screws).\n2. Provide 8mm cable gland cutout for power and external sensor wires.\n3. Add silicone gasket groove if outdoor waterproofing is needed.",
        "firmware_snippet": None,
        "host_snippet": None,
        "steps": [
            "1. Measure the microcontroller dimensions with digital calipers (e.g. 52mm x 28mm for ESP32 NodeMCU).",
            "2. Slice the enclosure model with 0.20mm layer height and 3 perimeters for strength.",
            "3. 3D print using PETG or PLA on your 3D printer.",
            "4. Mount the board using M2.5 nylon standoffs and snap the lid securely."
        ]
    }
]


class IoTProjectGuideService:
    """
    Intelligent IoT Lab Project Ideator & Step-by-Step Instruction Generator.
    Analyzes detected lab hardware combinations and suggests practical, runnable engineering projects.
    """

    def normalize_component_name(self, name: str) -> str:
        name = name.lower().replace(" ", "_").replace("-", "_")
        if "pi" in name or "raspberry" in name or "rpi" in name:
            return "raspberry_pi"
        if "microcontroller" in name or "esp32" in name or "arduino" in name or "stm32" in name or "pico" in name or "remote" in name:
            return "microcontroller"
        if "monitor" in name or "dell" in name or "screen" in name or "tv" in name:
            return "dell_monitor"
        if "soldering" in name or "iron" in name:
            return "soldering_station"
        if "printer" in name or "3d" in name:
            return "3d_printer"
        if "oscilloscope" in name or "scope" in name:
            return "oscilloscope"
        if "cell_phone" in name or "phone" in name:
            return "microcontroller"  # Common COCO proxy for rectangular dev board in lab setup
        return name

    def find_curated_matches(self, detected_components: List[str]) -> List[Dict[str, Any]]:
        norm_set = {self.normalize_component_name(c) for c in detected_components if c}
        results = []

        for proj in CURATED_PROJECTS:
            reqs = set(proj["matched_components"])
            # Match if all required components are in detected set, or if at least one key component matches
            if reqs.issubset(norm_set):
                results.append(proj)
            elif any(r in norm_set for r in reqs) and len(results) < 2:
                results.append(proj)

        # Fallback: if no specific match, return top projects
        if not results:
            results = CURATED_PROJECTS[:2]

        return results

    async def generate_custom_project_ideas(
        self,
        components: List[str],
        user_goal: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Synthesizes tailored IoT engineering project ideas using local SLM reasoning.
        """
        curated = self.find_curated_matches(components)
        comp_str = ", ".join(components) if components else "Raspberry Pi, Microcontroller"

        prompt = (
            f"You are an IoT Laboratory Systems Architect. A student has placed the following hardware on the workbench: {comp_str}.\n"
            f"Goal/Interest: {user_goal or 'Practical engineering IoT build'}.\n\n"
            f"Provide 2 realistic, high-value projects the student can build with these exact components.\n"
            f"For each project, include:\n"
            f"1. Project Title\n"
            f"2. Architecture & Communication Protocol (e.g. UART, I2C, MQTT)\n"
            f"3. Wiring & Pinout Guide (include 3.3V vs 5V voltage logic warnings!)\n"
            f"4. Step-by-Step Instructions\n"
            f"Keep the instructions concise, professional, and practical."
        )

        system_prompt = (
            "You are an expert Embedded Systems & IoT Lab Instructor. "
            "You provide practical, accurate wiring guides and firmware instructions for microcontrollers, Raspberry Pi, and lab sensors."
        )

        try:
            # Use quick local SLM (Qwen 2.5 1.5B responds in ~1.2s on CPU)
            resp = await llm_agent._call_single_model("qwen2.5:1.5b", system_prompt, prompt)
            if resp:
                llm_text = resp
                model_used = "qwen2.5:1.5b"
            else:
                llm_text = None
                model_used = "curated_kb"
        except Exception as e:
            logger.warning(f"[ProjectGuide] LLM call failed: {e}")
            llm_text = None
            model_used = "curated_kb"

        return {
            "detected_components": components,
            "curated_projects": curated,
            "llm_custom_suggestions": llm_text,
            "model_used": model_used
        }


# Global singleton instance
project_guide = IoTProjectGuideService()
