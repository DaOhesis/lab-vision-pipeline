#!/usr/bin/env python3
"""
Custom YOLO Fine-Tuning Pipeline for IoT Lab Equipment Detection
Leverages transfer learning from MS COCO pre-trained weights to train
a custom detector for 3D printers, Dell monitors, microcontrollers, etc.
"""

import os
import shutil
import argparse
from ultralytics import YOLO

def main():
    parser = argparse.ArgumentParser(description="Train custom YOLO detector on lab equipment")
    parser.add_argument("--data", default="training/data/equipment.yaml", help="Path to YOLO dataset yaml")
    parser.add_argument("--base-model", default="yolov8n.pt", help="Pretrained base model (yolov8n.pt or yolo11n.pt)")
    parser.add_argument("--epochs", type=int, default=100, help="Number of training epochs")
    parser.add_argument("--batch", type=int, default=16, help="Batch size (reduce to 8 if VRAM is constrained)")
    parser.add_argument("--imgsz", type=int, default=640, help="Image resolution size")
    parser.add_argument("--device", default="0", help="Training device: '0' for CUDA GPU, 'cpu' for CPU")
    parser.add_argument("--export-dir", default="models", help="Destination directory for deployed weights")
    args = parser.parse_args()

    print("==================================================")
    print("  YOLO Custom Lab Equipment Training Pipeline    ")
    print(f"  Base Weights: {args.base_model}")
    print(f"  Dataset:      {args.data}")
    print(f"  Epochs:       {args.epochs} | Batch: {args.batch} | ImgSz: {args.imgsz}")
    print(f"  Device:       {args.device}")
    print("==================================================")

    # 1. Load Pretrained Backbone
    print(f"\n[Step 1/4] Loading pretrained weights: {args.base_model}...")
    model = YOLO(args.base_model)

    # 2. Execute Training
    print("\n[Step 2/4] Commencing transfer learning training run...")
    results = model.train(
        data=args.data,
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        device=args.device,
        patience=15,             # Early stopping if no mAP improvement for 15 epochs
        save=True,
        plots=True,
        # Indoor lab domain augmentations
        hsv_h=0.015,             # Subtle hue shifts for lab lights
        hsv_s=0.5,               # Saturation variability
        hsv_v=0.4,               # Fluorescent brightness variability
        degrees=5.0,             # Minor rotation compensation
        translate=0.1,
        scale=0.2,
        shear=2.0,
        mosaic=0.8,              # Multi-object mosaic composition
        mixup=0.1,
        lr0=0.01,                # Initial learning rate
        lrf=0.01,                # Cosine annealing minimum learning rate
        project="runs/detect",
        name="lab_equipment_run"
    )

    # 3. Model Evaluation on Validation Split
    print("\n[Step 3/4] Evaluating best checkpoint on validation set...")
    metrics = model.val()
    print(f"  mAP@0.5:      {metrics.box.map50:.4f}")
    print(f"  mAP@0.5:0.95: {metrics.box.map:.4f}")

    # 4. Deploy Checkpoint to Models Directory
    best_weights_path = os.path.join(model.trainer.save_dir, "weights", "best.pt")
    if os.path.exists(best_weights_path):
        os.makedirs(args.export_dir, exist_ok=True)
        deployed_path = os.path.join(args.export_dir, "best.pt")
        shutil.copyfile(best_weights_path, deployed_path)
        print(f"\n[Step 4/4] Successfully deployed best checkpoint to: {deployed_path}")
        print("  FastAPI backend will automatically pick up this model on next restart.")
    else:
        print(f"\n[Warning] Could not locate best weights at: {best_weights_path}")

if __name__ == "__main__":
    main()
