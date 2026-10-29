#!/usr/bin/env python3
"""
Laptop Webcam Live Streamer for IoT Lab Vision Pipeline
Captures frames from your laptop's integrated webcam or USB camera
and streams them directly to the FastAPI computer vision backend.
"""

import time
import argparse
import sys
import cv2
import requests

def list_available_cameras(max_tested=4):
    """Probes available video capture indices."""
    available = []
    for i in range(max_tested):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            available.append(i)
            cap.release()
    return available

def main():
    parser = argparse.ArgumentParser(description="Stream laptop webcam to Lab Vision Backend")
    parser.add_argument("--device-index", type=int, default=0, help="Webcam device index (default: 0)")
    parser.add_argument("--url", default="http://localhost:8000/api/v1/telemetry/frame", help="FastAPI frame ingestion URL")
    parser.add_argument("--fps", type=float, default=5.0, help="Target transmission frame rate (FPS)")
    parser.add_argument("--width", type=int, default=800, help="Target frame width")
    parser.add_argument("--height", type=int, default=600, help="Target frame height")
    parser.add_argument("--quality", type=int, default=85, help="JPEG compression quality (1-100)")
    parser.add_argument("--no-preview", action="store_true", help="Run headlessly without OpenCV window")
    parser.add_argument("--device-id", default="laptop_webcam_01", help="Device identifier header")
    args = parser.parse_args()

    print("==================================================")
    print("  Laptop Webcam Ingestion Streamer                ")
    print(f"  Target URL:   {args.url}")
    print(f"  Webcam Index: {args.device_index}")
    print(f"  Target Rate:  {args.fps} FPS")
    print(f"  Resolution:   {args.width}x{args.height}")
    print("  Controls:     [Q] to quit, [+] / [-] adjust FPS")
    print("==================================================")

    # Initialize video capture
    cap = cv2.VideoCapture(args.device_index)
    if not cap.isOpened():
        print(f"[Error] Failed to access webcam at device index {args.device_index}.")
        available = list_available_cameras()
        if available:
            print(f"Available camera indices detected: {available}")
            print(f"Try running with: --device-index {available[0]}")
        else:
            print("No video capture devices found. Ensure webcam is connected and permissions are granted.")
        sys.exit(1)

    # Configure hardware resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)

    target_interval = 1.0 / max(args.fps, 0.5)
    frame_index = 0
    last_send_time = 0
    last_detections = []
    last_latency = 0.0

    session = requests.Session()

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[Warning] Empty frame captured from webcam. Retrying...")
                time.sleep(0.1)
                continue

            # Resize if webcam hardware didn't accept target resolution exactly
            if frame.shape[1] != args.width or frame.shape[0] != args.height:
                frame = cv2.resize(frame, (args.width, args.height))

            now = time.time()
            if now - last_send_time >= target_interval:
                last_send_time = now
                frame_index += 1

                # Encode frame to JPEG binary buffer
                encode_ok, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), args.quality])
                if not encode_ok:
                    continue

                payload = buffer.tobytes()
                headers = {
                    "Content-Type": "image/jpeg",
                    "X-Device-Id": args.device_id,
                    "X-Frame-Index": str(frame_index),
                    "X-Timestamp-Ms": str(round(now * 1000, 2))
                }

                t0 = time.time()
                try:
                    res = session.post(args.url, data=payload, headers=headers, timeout=2.0)
                    rtt_ms = round((time.time() - t0) * 1000, 1)

                    if res.status_code == 200:
                        data = res.json()
                        last_detections = data.get("detections", [])
                        last_latency = data.get("inference_latency_ms", 0.0)
                        equipment = data.get("equipment_counts", {})
                        equip_str = ", ".join([f"{k}: {v}" for k, v in equipment.items() if v > 0]) or "None"

                        print(f"[Webcam -> Host] Frame #{frame_index:04d} ({len(payload)//1024} KB) | RTT: {rtt_ms}ms | Infer: {last_latency}ms | Detected: {equip_str}")
                    else:
                        print(f"[Error] Backend HTTP {res.status_code}: {res.text}")
                except requests.exceptions.RequestException as e:
                    print(f"[Warning] Connection error: {e}. Is FastAPI running on {args.url}?")

            # Render local HUD preview window
            if not args.no_preview:
                preview = frame.copy()
                
                # Draw latest localized bounding boxes
                for det in last_detections:
                    box = det.get("box", [])
                    if len(box) == 4:
                        x1, y1, x2, y2 = map(int, box)
                        label = f"{det.get('class_name')} {int(det.get('confidence', 0)*100)}%"
                        cv2.rectangle(preview, (x1, y1), (x2, y2), (0, 255, 128), 2)
                        cv2.putText(preview, label, (x1, max(y1 - 6, 12)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 128), 1, cv2.LINE_AA)

                # Draw top status banner
                cv2.rectangle(preview, (0, 0), (args.width, 30), (20, 20, 20), -1)
                hud_text = f"LAPTOP WEBCAM | Frame #{frame_index} | Infer: {last_latency}ms | Objects: {len(last_detections)}"
                cv2.putText(preview, hud_text, (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 200), 1, cv2.LINE_AA)

                cv2.imshow("Laptop Webcam Streamer (Press 'Q' to quit)", preview)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == ord('Q') or key == 27:
                    break
                elif key == ord('+') or key == ord('='):
                    args.fps = min(args.fps + 1.0, 30.0)
                    target_interval = 1.0 / args.fps
                    print(f"[Setting] Increased stream rate to {args.fps:.1f} FPS")
                elif key == ord('-') or key == ord('_'):
                    args.fps = max(args.fps - 1.0, 1.0)
                    target_interval = 1.0 / args.fps
                    print(f"[Setting] Decreased stream rate to {args.fps:.1f} FPS")

    finally:
        cap.release()
        if not args.no_preview:
            cv2.destroyAllWindows()
        print("\n[Webcam] Streamer terminated successfully.")

if __name__ == "__main__":
    main()
