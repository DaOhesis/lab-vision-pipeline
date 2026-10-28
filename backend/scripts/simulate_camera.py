#!/usr/bin/env python3
"""
ESP32-CAM Hardware Simulator
Simulates the ESP32-CAM edge device by streaming synthetic or webcam frames
to the local FastAPI backend endpoint.
"""

import time
import argparse
import numpy as np
import cv2
import requests

def create_synthetic_lab_frame(frame_idx: int) -> bytes:
    """Creates a synthetic 800x600 test frame representing an IoT lab test bench."""
    # Dark modern workbench background
    img = np.zeros((600, 800, 3), dtype=np.uint8)
    img[:] = (35, 30, 30)  # Dark slate gray

    # Draw workbench grid lines
    for x in range(0, 800, 50):
        cv2.line(img, (x, 0), (x, 600), (45, 42, 42), 1)
    for y in range(0, 600, 50):
        cv2.line(img, (0, y), (800, y), (45, 42, 42), 1)

    # Simulated Monitor (Dell monitor mockup)
    cv2.rectangle(img, (80, 100), (380, 350), (60, 60, 60), -1)
    cv2.rectangle(img, (90, 110), (370, 310), (20, 20, 20), -1)
    cv2.putText(img, "Dell UltraSharp Display", (120, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 180), 2)
    cv2.rectangle(img, (220, 350), (240, 420), (50, 50, 50), -1)  # Stand
    cv2.rectangle(img, (180, 420), (280, 435), (70, 70, 70), -1)  # Base

    # Simulated Microcontroller Dev Board (ESP32 / Arduino mockup)
    cv2.rectangle(img, (480, 380), (660, 490), (25, 90, 30), -1)  # Green PCB
    cv2.rectangle(img, (530, 400), (610, 470), (20, 20, 20), -1)  # SoC Shield
    cv2.putText(img, "ESP32-WROOM", (535, 440), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
    
    # GPIO pin headers
    for px in range(490, 650, 15):
        cv2.circle(img, (px, 390), 2, (180, 180, 50), -1)
        cv2.circle(img, (px, 480), 2, (180, 180, 50), -1)

    # Simulated 3D Printer Mockup
    cv2.rectangle(img, (450, 80), (740, 340), (70, 70, 80), 2)  # Frame
    cv2.rectangle(img, (500, 270), (690, 290), (120, 100, 50), -1)  # Heatbed
    cv2.putText(img, "3D Printer (Ender/Prusa)", (480, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (220, 220, 220), 1)

    # Frame details overlay
    cv2.putText(img, f"SIMULATED ESP32-CAM | Frame: #{frame_idx}", (20, 570), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 200), 1)
    cv2.putText(img, time.strftime("%Y-%m-%d %H:%M:%S"), (580, 570), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (160, 160, 160), 1)

    # Encode as JPEG bytes (matching ESP32-CAM output)
    _, buffer = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    return buffer.tobytes()

def main():
    parser = argparse.ArgumentParser(description="ESP32-CAM Simulator for Lab Vision Backend")
    parser.add_argument("--url", default="http://localhost:8000/api/v1/telemetry/frame", help="FastAPI frame ingestion URL")
    parser.add_argument("--interval", type=float, default=1.5, help="Interval between frames in seconds")
    parser.add_argument("--webcam", action="store_true", help="Use local PC webcam instead of synthetic frame")
    parser.add_argument("--device-id", default="simulator_cam_01", help="Device identifier header")
    args = parser.parse_args()

    print("==================================================")
    print("  ESP32-CAM Hardware Simulator Initialized        ")
    print(f"  Target: {args.url}")
    print(f"  Interval: {args.interval}s | Device: {args.device_id}")
    print("==================================================")

    cap = None
    if args.webcam:
        print("[Simulator] Accessing local webcam (Device 0)...")
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("[Simulator] ERROR: Failed to open webcam. Falling back to synthetic frames.")
            cap = None

    frame_index = 0
    try:
        while True:
            frame_index += 1
            if cap is not None and cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    _, buf = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
                    payload_bytes = buf.tobytes()
                else:
                    payload_bytes = create_synthetic_lab_frame(frame_index)
            else:
                payload_bytes = create_synthetic_lab_frame(frame_index)

            headers = {
                "Content-Type": "image/jpeg",
                "X-Device-Id": args.device_id,
                "X-Frame-Index": str(frame_index),
                "X-Timestamp-Ms": str(round(time.time() * 1000, 2))
            }

            t0 = time.time()
            try:
                response = requests.post(args.url, data=payload_bytes, headers=headers, timeout=5.0)
                dur_ms = round((time.time() - t0) * 1000, 1)
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"[Sim -> Host] Frame #{frame_index:04d} posted ({len(payload_bytes)//1024} KB) in {dur_ms}ms | Detections: {data.get('total_detections')} | Infer: {data.get('inference_latency_ms')}ms")
                else:
                    print(f"[Sim -> Host] HTTP Error {response.status_code}: {response.text}")
            except requests.exceptions.RequestException as e:
                print(f"[Sim -> Host] Connection error: {e}. Is FastAPI running on {args.url}?")

            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n[Simulator] Simulator stopped by user.")
    finally:
        if cap:
            cap.release()

if __name__ == "__main__":
    main()
