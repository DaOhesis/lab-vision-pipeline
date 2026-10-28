#!/usr/bin/env python3
"""
YOLO to ONNX Exporter
Exports fine-tuned PyTorch weights (.pt) to ONNX format for accelerated local CPU/GPU inference.
"""

import os
import argparse
from ultralytics import YOLO

def main():
    parser = argparse.ArgumentParser(description="Export trained YOLO model to ONNX format")
    parser.add_argument("--weights", default="models/best.pt", help="Path to input PyTorch weights file")
    parser.add_argument("--imgsz", type=int, default=640, help="Image resolution dimension")
    parser.add_argument("--half", action="store_true", help="Export with FP16 half-precision")
    parser.add_argument("--opset", type=int, default=17, help="ONNX opset version")
    args = parser.parse_args()

    if not os.path.exists(args.weights):
        print(f"[Error] Weights file not found: {args.weights}")
        return

    print("==================================================")
    print("  YOLO to ONNX Optimization Exporter             ")
    print(f"  Input: {args.weights} | ImgSz: {args.imgsz}")
    print(f"  FP16:  {args.half} | Opset: {args.opset}")
    print("==================================================")

    model = YOLO(args.weights)
    exported_path = model.export(
        format="onnx",
        imgsz=args.imgsz,
        half=args.half,
        opset=args.opset,
        dynamic=False,
        simplify=True
    )

    print(f"\n[Success] ONNX Model exported to: {exported_path}")

if __name__ == "__main__":
    main()
