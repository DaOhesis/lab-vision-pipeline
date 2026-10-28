# IoT Lab Vision Intelligence System
## Architecture Blueprint & Technical Pipeline Specification

---

## 1. System Architecture & Data Flow

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

### 1.1 Edge-to-Host Communication Protocol Evaluation
For streaming frames from an ESP32-CAM to a local FastAPI backend across a local area network (LAN), three primary transmission patterns exist:

| Criteria | HTTP POST (Binary / Multipart) | WebSockets (ESP32 Client) | MQTT (Broker-mediated) |
| :--- | :--- | :--- | :--- |
| **ESP32 Memory Footprint** | **Minimal (~8 KB stack)** | Moderate (~25–35 KB stack) | High (Broker buffers + client) |
| **Brownout / Crash Resilience** | **Highest (Stateless)** | Low (Connection state leaks) | Moderate (Dependent on broker) |
| **Max Frame Rate on LAN** | **5–12 FPS (SVGA/XGA)** | 8–15 FPS (Persistent TCP) | 1–3 FPS (MTU fragmentation risk) |
| **Network Reconnect Overhead** | Zero (Handled per request) | High (Handshake on every drop)| High (Keep-alive negotiation) |
| **Implementation Complexity** | Low & Standardized | Medium (ESP-IDF / WebSockets) | High (Topic chunking required) |

#### Architectural Decision: Chunked HTTP POST (Snapshot / Continuous Ingestion)
1. **Payload Transmission**: The ESP32-CAM opens an HTTP `POST` request to `http://<HOST_IP>:8000/api/v1/telemetry/frame`. The frame is sent directly as `image/jpeg` raw binary octet-stream (or standard `multipart/form-data` with metadata headers: `X-Device-ID`, `X-Capture-Timestamp`, and `X-Frame-Index`). 
2. **Buffer Safety**: Sending raw JPEG buffers directly from ESP32 PSRAM minimizes memory copying and eliminates base64 encoding overhead (which consumes 33% more bandwidth and CPU cycles on the Xtensa LX6 dual-core chip).
3. **Transmission Modes**:
   - **Triggered / Periodic Mode** (Default): ESP32-CAM transmits a snapshot every 1 to 3 seconds. Ideal for static inventory, tracking 3D print progress, and monitoring bench equipment without overheating the OV2640 sensor.
   - **Continuous Stream Mode**: Tight loop executing `esp_camera_fb_get()`, `http.POST()`, and `esp_camera_fb_return()` with yield semantics to feed the watchdog timer.

### 1.2 End-to-End Data Pipeline
1. **Acquisition**: The OV2640 sensor samples the scene via DMA into an internal frame buffer allocated in external PSRAM.
2. **Egress**: The ESP32 C++ firmware validates Wi-Fi connectivity, packages the frame with hardware timestamps, and transmits it via HTTP `POST`.
3. **Ingestion & Dequeueing**: FastAPI receives the byte stream in an asynchronous non-blocking route. The payload is pushed into an in-memory `asyncio.Queue(maxsize=1)`. 
   > **Drop-Oldest Strategy**: If inference is still executing when a new frame arrives, the stale frame is dropped immediately. This eliminates queue latency buildup, ensuring the dashboard always visualizes current physical reality.
4. **Inference Execution**: A worker thread runs the PyTorch/Ultralytics model inference on the decoded image, producing bounding box coordinates, class labels, and confidence vectors.
5. **Client Broadcast**: FastAPI packages the detection metadata and frame into a unified JSON/binary payload and broadcasts it over a WebSocket connection (`/api/v1/ws/stream`) to all connected Next.js dashboard instances.

---

## 2. Component Specifications

### 2.1 Firmware (ESP32-CAM C++ / FreeRTOS)

#### Hardware & Power Considerations
- **Hardware Profile**: AI-Thinker ESP32-CAM module (ESP32-D0WDQ6, 520 KB SRAM, 4 MB external PSRAM, OV2640 2MP camera module).
- **Power Decoupling**: The OV2640 draws sudden current spikes (up to 310 mA during Wi-Fi transmission + sensor power-up). Powering via a dedicated 5V rail with an external $100\,\mu\text{F}$ to $470\,\mu\text{F}$ electrolytic capacitor across `VCC` and `GND` is mandatory to avoid random brownout resets.

#### Camera Sensor Configuration
```text
Pixel Format:       PIXFORMAT_JPEG (hardware compressed on OV2640 ASIC)
Frame Size:         FRAMESIZE_SVGA (800x600) for balanced detail vs network payload,
                    or FRAMESIZE_XGA (1024x768) for fine component inspection
JPEG Quality:       10 - 12 (Scale: 0-63; lower values yield higher image fidelity)
Frame Buffers:      fb_count = 2 (Enables double-buffering via DMA in PSRAM)
Grab Mode:          CAMERA_GRAB_LATEST (Discard stale DMA buffers)
```

#### Core C++ Libraries
- `esp_camera.h`: Low-level Espressif camera driver handling I2C SCCB configuration and high-speed DMA bus capture.
- `WiFi.h`: Station-mode networking with static IP assignment (eliminates DHCP discovery lag).
- `HTTPClient.h` / `esp_http_client.h`: Optimized HTTP client supporting chunked streaming and custom header injection.
- `esp_task_wdt.h`: FreeRTOS task watchdog to automatically recover and reboot the board if the camera pipeline stalls.

---

### 2.2 Backend (FastAPI Architecture)

#### Threading & Concurrency Model
- **Async I/O Layer**: `uvicorn` running FastAPI with `async/await` handling incoming HTTP connections and outgoing WebSockets without blocking.
- **Dedicated Inference Worker**: Object detection via PyTorch utilizes native C++/CUDA bindings that occupy the CPU/GPU. Running model execution directly inside an `async def` route would block the Python event loop, causing dropped frames and sluggish WebSockets. Model inference is therefore delegated to an isolated thread pool executor (`asyncio.to_thread` or `concurrent.futures.ThreadPoolExecutor`).

#### Endpoints & Routing Topology
```text
POST /api/v1/telemetry/frame       <- Ingests raw JPEG payload from ESP32-CAM
GET  /api/v1/telemetry/latest      <- REST fallback for latest frame and detections
GET  /api/v1/inventory/summary     <- Returns counts of active lab equipment
WS   /api/v1/ws/stream             <- Full-duplex WebSocket streaming detections to Next.js
GET  /health                       <- Sensor uptime and inference latency diagnostics
```

#### Ingestion & State Pipeline
```
[ESP32 POST] ──> [FastAPI Route] ──> [LIFO In-Memory Ring Buffer]
                                                │
                                                ▼ (Worker Thread)
                                     [YOLO Inference Engine]
                                                │
                                    ┌───────────┴───────────┐
                                    ▼                       ▼
                         [Annotated Frame / BBoxes]   [Telemetry DB / State]
                                    │                       │
                                    └───────────┬───────────┘
                                                ▼
                                    [WebSocket ConnectionManager]
                                                │
                                                ▼
                                    [Next.js Client(s)]
```

---

### 2.3 Vision Model (PyTorch & Ultralytics YOLO)

#### Model Selection: YOLO11n / YOLOv8n (Nano Variant)
For local desktop/laptop inference (CPU or consumer GPU), **YOLO11n** or **YOLOv8n** is recommended:
- **Parameter Count**: ~2.6M to 3.2M parameters.
- **Inference Latency**:
  - *Modern CPU (Intel i7 / Ryzen 7 / Apple Silicon)*: 12–25 ms per frame.
  - *Dedicated GPU (NVIDIA RTX 3050+)*: 2–5 ms per frame.
- **Accuracy**: Outperforms older models (YOLOv3-tiny, MobileNet-SSD v2) in detecting dense, overlapping electronic components and varied aspect ratios.
- **Integration**: Loaded into memory once during FastAPI application startup (`lifespan` context) to avoid per-request model reload overhead.

#### Custom Lab Equipment Taxonomy
The model is fine-tuned to classify key IoT lab targets:
```yaml
Classes:
  0: "3d_printer"          # Enclosed/open-bed additive manufacturing machines
  1: "dell_monitor"        # Flat/curved displays with identifiable bezels and stands
  2: "microcontroller"     # ESP32, Arduino, Raspberry Pi dev boards
  3: "oscilloscope"        # Test bench benchtop instruments
  4: "soldering_station"   # Soldering irons, heat guns, temperature display bases
```

#### Inference Output Contract
The vision service yields normalized spatial coordinates:
```json
{
  "device_id": "esp32_cam_lab_01",
  "timestamp": 1793264100.125,
  "inference_latency_ms": 14.8,
  "equipment_counts": {
    "3d_printer": 1,
    "dell_monitor": 2,
    "microcontroller": 3
  },
  "detections": [
    {
      "class": "3d_printer",
      "confidence": 0.93,
      "box": [120, 85, 430, 510]
    },
    {
      "class": "microcontroller",
      "confidence": 0.88,
      "box": [510, 420, 590, 480]
    }
  ]
}
```

---

### 2.4 Frontend (Next.js Real-Time Dashboard)

#### Architecture & State Synchronization
- **Framework**: Next.js (App Router) running locally on `http://localhost:3000`.
- **Communication Channel**: Client-side WebSocket connection (`ws://localhost:8000/api/v1/ws/stream`) managed by a custom React hook (`useLabStream`).
- **Rendering Strategy**:
  - Raw frame updates arrive as binary blobs or base64 strings.
  - An **HTML5 Canvas overlay** sits atop the video stream. Instead of baking bounding boxes into the image on the backend (which wastes CPU and prevents interaction), raw frames are drawn to the canvas, and vectors are dynamically rendered client-side.
  - Allows toggling specific class bounding boxes (e.g., hide monitors, isolate microcontrollers) and inspecting confidence values on mouse hover.

#### UI Component Hierarchy
```
DashboardLayout
├── Header (Connection status, FPS counter, latency tracker)
├── MainWorkspace (Grid layout)
│   ├── VideoViewport
│   │   ├── RawFrameImage / Video Element
│   │   ├── DynamicCanvasOverlay (Bounding boxes, labels, centroid tracking)
│   │   └── ViewportControls (Confidence threshold slider, resolution toggle)
│   ├── EquipmentTelemetryPanel
│   │   ├── MetricCards (Total counts, active 3D printers, board count)
│   │   └── AnomalyAlerts (e.g., "Equipment missing from bench 2")
│   └── DetectionEventLog (Tabular chronological audit log of detections)
```

---

## 3. Data & Training Pipeline

```
+-----------------------------------------------------------------------------------+
|                        LAB EQUIPMENT TRAINING PIPELINE                            |
+-----------------------------------------------------------------------------------+
  [ESP32-CAM In-Situ Capture] ──> [CVAT / Label Studio] ──> [Stratified Split 70/20/10]
              │                              │                            │
   Vary Angles & Lighting           Class Labels & BBoxes         Train / Val / Test
              │                              │                            │
              ▼                              ▼                            ▼
  [Domain Augmentation] ─────────> [YOLO Transfer Learn] ───> [ONNX / PyTorch Export]
  (HSV, Perspective, Blur)          (COCO Pretrained Backbone)
```

### Step 1: In-Situ Data Collection
*Avoid using web-scraped images or generic datasets.* The OV2640 sensor exhibits distinct optical properties:
- Mild barrel distortion from wide-angle lenses.
- High noise in low lab lighting.
- Narrow dynamic range compared to smartphone sensors.

**Capture Strategy**:
- Position the ESP32-CAM in its intended deployment positions (tripod, ceiling mount, or desk rig).
- Collect **300 to 500 images** across diverse conditions:
  - Lab lights ON vs lights dimmed.
  - Equipment placed in varied orientations (e.g., microcontrollers with wires attached vs bare boards).
  - Varied backgrounds (wooden workbenches, anti-static blue mats, soldering smoke).

### Step 2: Annotation Protocol (Label Studio / CVAT)
- Utilize open-source tools running locally (**CVAT** or **Label Studio**).
- **Bounding Box Guidelines**:
  - Tight boundaries excluding trailing cable clutter unless essential to device identification.
  - Partially occluded equipment (e.g., a monitor behind a 3D printer) must be labeled if $\ge 30\%$ of the body is visible.
- Export annotations directly in standard **YOLO Darknet format** (`class_id center_x center_y width height` normalized between $0.0$ and $1.0$).

### Step 3: Domain-Specific Data Augmentation
Prior to training, configure augmentations that simulate physical lab conditions:
- **HSV Shifts**: Hue $\pm 0.015$, Saturation $\pm 0.5$, Value $\pm 0.3$ (simulates fluorescent flicker and sunlight shifts).
- **Perspective & Affine Transforms**: Shear $\pm 2.0^{\circ}$, Scale factor $\pm 0.2$ (simulates minor camera positioning offsets).
- **Mosaic & MixUp**: Enabled during the first 80% of training epochs to help the model learn small objects (microcontrollers) adjacent to large equipment (monitors).

### Step 4: Model Training & Evaluation
1. **Transfer Learning**: Initialize training from `yolov8n.pt` or `yolo11n.pt` pre-trained on MS COCO.
2. **Hyperparameters**:
   - Image resolution: $640 \times 640$ (rescaled preserving aspect ratio).
   - Batch size: 16 (or 32 if 8GB+ VRAM is available).
   - Epochs: 100 with early stopping patience of 15 epochs.
   - Optimizer: AdamW or SGD with Cosine Annealing learning rate schedule ($lr_0 = 0.01$, $lrf = 0.01$).
3. **Verification Metrics**:
   - $\text{mAP}@0.5 > 0.88$ across all equipment classes.
   - $\text{mAP}@[0.5:0.95] > 0.65$.
   - Confirm low confusion matrix overlap between small circuit boards and breadboard accessories.

---

## 4. Phased Execution Roadmap

```
Phase 1: Hardware & Network Bringup
├── Configure ESP32-CAM pinouts & flash camera baseline
├── Calibrate OV2640 registers (exposure, contrast, white balance)
└── Validate raw HTTP POST frame delivery to local listener
       │
Phase 2: Backend Core & Mock Pipeline
├── Implement FastAPI ingestion endpoint with LIFO queue
├── Build WebSocket broadcast manager
└── Test end-to-end stream latency with simulated frames
       │
Phase 3: Dataset Collection & Model Training
├── Deploy ESP32-CAM to capture raw lab environment imagery
├── Annotate images using CVAT/Label Studio in YOLO format
└── Train YOLO11n using PyTorch transfer learning & validate mAP
       │
Phase 4: Vision Engine Integration
├── Load fine-tuned weights into FastAPI lifespan context
├── Benchmark local CPU/GPU inference latency
└── Stream structured detection metadata over WebSockets
       │
Phase 5: Next.js Frontend Dashboard
├── Build responsive UI layout with Tailwind CSS
├── Implement useLabStream WebSocket hook with auto-reconnect
└── Build HTML5 Canvas dynamic bounding box overlay
       │
Phase 6: Calibration & Hardening
├── Fine-tune confidence thresholds to eliminate false positives
├── Test ESP32-CAM auto-reconnect on router reboot
└── End-to-end stress testing (continuous multi-hour operation)
```

### Phase Breakdown

#### Phase 1: Hardware & Network Bringup
- Verify 5V power supply stability and attach decoupling capacitors to prevent brownouts.
- Write and flash baseline ESP32 C++ firmware configuring Wi-Fi in Station Mode.
- Test image capture at `FRAMESIZE_SVGA` and measure frame transfer times over the local router.

#### Phase 2: Backend Core & Ingestion Skeleton
- Set up a Python virtual environment and initialize FastAPI.
- Build the `POST /api/v1/telemetry/frame` endpoint to accept byte streams and save snapshots to disk for debugging.
- Establish the WebSocket broadcaster and confirm bidirectional communication using a test script.

#### Phase 3: Dataset Collection & Model Training
- Mount the ESP32-CAM in the lab and run a simple capture script to collect images across different times of day.
- Label 300–500 samples in CVAT/Label Studio covering all target classes.
- Train YOLO11n on local GPU (or Google Colab) and export weights (`best.pt`).

#### Phase 4: Model Integration & Inference Optimization
- Integrate the trained weights into the FastAPI pipeline.
- Implement the non-blocking worker thread so image ingestion and model inference operate concurrently.
- Validate that end-to-end processing (capture $\to$ transmit $\to$ infer) stays under $150\,\text{ms}$.

#### Phase 5: Next.js Frontend Development
- Initialize the Next.js client with Tailwind CSS.
- Build the live dashboard layout: video canvas, equipment counters, and status badges.
- Connect to `ws://localhost:8000/api/v1/ws/stream` and verify real-time bounding box rendering.

#### Phase 6: System Calibration & Reliability Tuning
- Adjust optical parameters on the OV2640 (gain ceiling, automatic white balance, edge enhancement) to optimize object edge clarity.
- Stress-test the system: disconnect and reconnect Wi-Fi to confirm automatic ESP32 recovery and frontend WebSocket reconnection.
