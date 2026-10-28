# IoT Lab Vision Intelligence Pipeline

An end-to-end edge-to-cloud computer vision pipeline designed for real-time laboratory equipment tracking (3D printers, monitors, microcontrollers, oscilloscopes, soldering stations) using an **ESP32-CAM**, **FastAPI**, **PyTorch / YOLO11**, and **Next.js**.

All components run locally on your machine with low-latency streaming and zero containerization overhead.

---

## System Architecture

```
+------------------+         Local Wi-Fi (LAN)         +-----------------------------------------+
|    ESP32-CAM     |  ===============================>  |              LOCAL BACKEND              |
| (AI-Thinker Dev) |    HTTP POST (Multipart/Binary)   |                (FastAPI)                |
|                  |                                   |  +-----------------------------------+  |
| - OV2640 Sensor  |                                   |  | Ingestion: POST /api/v1/frame     |  |
| - C++ / FreeRTOS |                                   |  +-----------------+-----------------+  |
+------------------+                                   |                    |                    |
                                                       |         [asyncio.Queue (LIFO)]          |
                                                       |                    v                    |
                                                       |  +-----------------------------------+  |
                                                       |  | Vision Engine (PyTorch / YOLO11n) |  |
                                                       |  | - Class Inference & Box Regress   |  |
                                                       |  | - Equipment Count & Spatial Map   |  |
                                                       |  +-----------------+-----------------+  |
                                                       |                    |                    |
                                                       |        [WebSocket Broadcast Hub]        |
                                                       +--------------------+--------------------+
                                                                            |  ws://localhost:8000/ws
                                                                            v
                                                       +-----------------------------------------+
                                                       |            LOCAL DASHBOARD              |
                                                       |               (Next.js)                 |
                                                       |                                         |
                                                       | - HTML5 Canvas Bounding Box Overlay    |
                                                       | - Equipment Telemetry & Inventory Tally |
                                                       | - Sensor Latency & Health Indicator     |
                                                       +-----------------------------------------+
```

---

## Repository Structure

```
.
├── ARCHITECTURE_BLUEPRINT.md    # Detailed architectural design & trade-off specification
├── README.md                    # Master setup & running guide (this document)
├── backend/                     # FastAPI Computer Vision Server
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes.py        # HTTP POST ingestion & WebSocket endpoints
│   │   │   └── schemas.py       # Pydantic telemetry & bounding box schemas
│   │   ├── services/
│   │   │   ├── detector.py      # Thread-safe YOLO inference engine
│   │   │   └── stream_manager.py# WebSocket connection pool & telemetry broadcast
│   │   ├── config.py            # Application settings & class taxonomy
│   │   └── main.py              # Application entrypoint & CORS middleware
│   ├── scripts/
│   │   └── simulate_camera.py   # Hardware simulator (test without physical ESP32)
│   ├── requirements.txt         # Python dependencies
│   └── README.md
├── frontend/                    # Next.js 14 Real-Time Telemetry Dashboard
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx       # Root layout
│   │   │   ├── page.tsx         # Real-time dashboard view
│   │   │   └── globals.css      # Dark IoT theme styles
│   │   ├── components/
│   │   │   ├── Header.tsx       # Live status, latency & FPS counters
│   │   │   ├── VideoCanvas.tsx  # Interactive canvas & SVG bounding box overlays
│   │   │   ├── InventoryCards.tsx# Equipment count cards
│   │   │   └── DetectionFeed.tsx# Chronological detection event audit log
│   │   ├── hooks/
│   │   │   └── useLabStream.ts  # Auto-reconnecting WebSocket client hook
│   │   └── types/
│   │       └── telemetry.ts     # TypeScript data contracts
│   ├── package.json
│   ├── tailwind.config.ts
│   └── README.md
├── firmware/                    # ESP32-CAM C++ / FreeRTOS Firmware
│   ├── include/
│   │   ├── camera_pins.h        # AI-Thinker pin definitions
│   │   └── config.h             # Wi-Fi credentials & host endpoint
│   ├── src/
│   │   └── main.cpp             # DMA capture, watchdog timer & HTTP POST stream
│   ├── platformio.ini           # PlatformIO configuration (PSRAM enabled)
│   └── README.md
├── training/                    # Custom Lab Equipment Training Pipeline
│   ├── data/
│   │   └── equipment.yaml       # YOLO dataset definition (3D printer, monitor, etc.)
│   ├── scripts/
│   │   ├── capture_dataset.py   # In-situ dataset collection tool
│   │   ├── train.py             # Transfer learning training script
│   │   └── export_onnx.py       # Export PyTorch weights to ONNX format
│   └── README.md
└── models/                      # Trained YOLO weights (.pt / .onnx)
    └── README.md
```

---

## Quickstart: Running the System Locally

### Step 1: Start the FastAPI Backend

Open **Terminal 1**:
```bash
cd backend

# Create & activate a Python virtual environment
python -m venv venv

# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Linux / macOS:
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start backend server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
*The backend is now live at `http://localhost:8000` (Swagger docs: `http://localhost:8000/docs`).*

---

### Step 2: Start the Next.js Frontend Dashboard

Open **Terminal 2**:
```bash
cd frontend

# Install Node dependencies
npm install

# Start development dashboard
npm run dev
```
*Open your browser and navigate to **`http://localhost:3000`**.*

---

### Step 3: Stream Frames to the Backend

You can stream frames either via the included **software simulator** or via the **physical ESP32-CAM**:

#### Option A: Run the Camera Simulator (No Hardware Required)
Open **Terminal 3** (with your Python `venv` active):
```bash
# Stream synthetic laboratory test bench frames every 1.5s:
python backend/scripts/simulate_camera.py

# Or stream frames directly from your PC's webcam:
python backend/scripts/simulate_camera.py --webcam --interval 1.0
```

#### Option B: Flash the Physical ESP32-CAM
1. Edit [`firmware/include/config.h`](firmware/include/config.h) with your Wi-Fi SSID, password, and local PC IP.
2. Connect GPIO 0 to GND and flash using PlatformIO:
   ```bash
   cd firmware
   pio run --target upload
   ```
3. Disconnect GPIO 0 and reboot the board. It will automatically transmit frames to your local backend over Wi-Fi.

---

## Custom Equipment Model Training

To train the detector on your specific laboratory equipment:
1. **Capture samples**: Run `python training/scripts/capture_dataset.py --output-dir training/data/raw`.
2. **Label bounding boxes**: Use [Label Studio](https://labelstud.io) and export in YOLO format.
3. **Train**:
   ```bash
   python training/scripts/train.py --epochs 100 --batch 16 --device 0
   ```
4. Checkpoints are automatically saved to `models/best.pt`, which FastAPI picks up immediately on reload.

---

## API & WebSocket Reference

- `POST /api/v1/telemetry/frame`: Ingests binary JPEG frames from the ESP32-CAM.
- `GET /api/v1/telemetry/latest`: Retrieves the latest detection metadata.
- `GET /api/v1/telemetry/latest/frame`: Retrieves the latest JPEG image snapshot.
- `GET /api/v1/inventory/summary`: Returns active counts for all equipment classes.
- `WS /api/v1/ws/stream`: Full-duplex WebSocket stream feeding bounding boxes, counts, and base64 frames to Next.js.
- `GET /health`: Diagnostic health check (model status, memory, connected clients).
