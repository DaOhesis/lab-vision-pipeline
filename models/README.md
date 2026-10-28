# Vision Models Directory (`models/`)

This directory houses the trained PyTorch / ONNX model weight files for the IoT Lab Vision pipeline.

- **`best.pt`**: Place your fine-tuned YOLO model weights here after running `python training/scripts/train.py`.
- **Automatic Fallback**: If `models/best.pt` is not found, the FastAPI backend will automatically download and use `yolov8n.pt` (MS COCO pretrained) for immediate testing and verification.
