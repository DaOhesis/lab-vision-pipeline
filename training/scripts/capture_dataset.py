#!/usr/bin/env python3
"""
IoT Lab Dataset Collector
Tool for gathering training images directly from the ESP32-CAM stream or a local camera.
Prevents domain gap by ensuring the dataset matches the optical profile of the edge sensor.
"""

import os
import time
import argparse
import urllib.request
import cv2
import numpy as np

def main():
    parser = argparse.ArgumentParser(description="Capture training dataset from ESP32-CAM or local webcam")
    parser.add_argument("--output-dir", default="training/data/raw", help="Directory where captured images are stored")
    parser.add_argument("--source", default="webcam", choices=["webcam", "esp32_url"], help="Stream source")
    parser.add_argument("--esp32-url", default="http://192.168.1.100/capture", help="Direct snapshot URL if ESP32 serves /capture")
    parser.add_argument("--camera-index", type=int, default=0, help="Webcam device index")
    parser.add_argument("--auto-interval", type=float, default=0, help="If > 0, automatically snap a photo every N seconds")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    print("==================================================")
    print("  IoT Lab Equipment Dataset Capture Tool          ")
    print(f"  Target Output: {args.output_dir}")
    print("  Controls:")
    print("    [SPACE] - Capture single photo")
    print("    [A]     - Toggle automatic interval capture")
    print("    [Q/ESC] - Save and Exit")
    print("==================================================")

    cap = None
    if args.source == "webcam":
        cap = cv2.VideoCapture(args.camera_index)
        if not cap.isOpened():
            print(f"[Error] Failed to open webcam at index {args.camera_index}")
            return

    count = len(os.listdir(args.output_dir))
    auto_mode = args.auto_interval > 0
    last_auto_snap = time.time()

    try:
        while True:
            frame = None
            if args.source == "webcam":
                ret, frame = cap.read()
                if not ret:
                    print("[Warning] Failed to read frame from webcam.")
                    time.sleep(0.1)
                    continue
            else:
                # Fetch snapshot from ESP32 URL
                try:
                    req = urllib.request.urlopen(args.esp32_url, timeout=3.0)
                    img_array = np.asarray(bytearray(req.read()), dtype=np.uint8)
                    frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                except Exception as e:
                    print(f"[Warning] Failed to fetch frame from {args.esp32_url}: {e}")
                    time.sleep(1.0)
                    continue

            # Overlay information on preview display
            display = frame.copy()
            status_text = f"Captured: {count} | Auto: {'ON (' + str(args.auto_interval) + 's)' if auto_mode else 'OFF'}"
            cv2.putText(display, status_text, (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 128), 2)
            cv2.putText(display, "Press [SPACE] to Snap, [A] to Toggle Auto, [Q] to Quit", (20, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (220, 220, 220), 1)

            cv2.imshow("Dataset Capture Utility", display)
            key = cv2.waitKey(20) & 0xFF

            # Handle automatic interval capture
            now = time.time()
            trigger_save = False

            if auto_mode and (now - last_auto_snap >= args.auto_interval):
                trigger_save = True
                last_auto_snap = now

            if key == 32:  # SPACE bar
                trigger_save = True
            elif key == ord('a') or key == ord('A'):
                auto_mode = not auto_mode
                if args.auto_interval <= 0:
                    args.auto_interval = 2.0
                last_auto_snap = now
                print(f"[Mode] Auto capture toggled: {'ON' if auto_mode else 'OFF'}")
            elif key == ord('q') or key == ord('Q') or key == 27:
                break

            if trigger_save:
                count += 1
                filename = f"lab_equip_{int(now)}_{count:04d}.jpg"
                filepath = os.path.join(args.output_dir, filename)
                cv2.imwrite(filepath, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
                print(f"[Captured] Saved #{count:04d} -> {filepath}")
                # Flash preview green
                cv2.rectangle(display, (0, 0), (display.shape[1], display.shape[0]), (0, 255, 0), 10)
                cv2.imshow("Dataset Capture Utility", display)
                cv2.waitKey(50)

    finally:
        if cap:
            cap.release()
        cv2.destroyAllWindows()
        print(f"\n[Completed] Total samples stored in {args.output_dir}: {count}")

if __name__ == "__main__":
    main()
