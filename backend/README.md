# FastAPI Computer Vision Backend (`backend/`)

This directory contains the local FastAPI backend server that ingests frames from the ESP32-CAM (or camera simulator), executes YOLO object detection inference, manages active equipment inventories, and streams telemetry over WebSockets to the Next.js dashboard.

---

## 1. Setup & Installation (Local Environment)

### Step 1: Create a Python Virtual Environment
Open a terminal in the root or `backend` folder:
```bash
cd backend
python -m venv venv
```

Activate the virtual environment:
- **Windows (PowerShell)**:
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```
- **Windows (Command Prompt)**:
  ```cmd
  .\venv\Scripts\activate.bat
  ```
- **Linux / macOS**:
  ```bash
  source venv/bin/activate
  ```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 2. Running the Server

Start the FastAPI application with live auto-reload enabled:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The server will be reachable at:
- **API Base URL**: `http://localhost:8000`
- **Interactive Swagger Documentation**: `http://localhost:8000/docs`
- **Health Diagnostics**: `http://localhost:8000/health`
- **Real-Time WebSocket Stream**: `ws://localhost:8000/api/v1/ws/stream`

---

## 3. Testing with the ESP32-CAM Simulator

If you do not have the physical ESP32-CAM powered on yet, you can test the entire pipeline end-to-end using the included hardware simulator script.

In a separate terminal (with virtual environment active):
```bash
# Transmit synthetic lab frames every 1.5 seconds
python scripts/simulate_camera.py

# Or transmit your PC's local webcam stream directly:
python scripts/simulate_camera.py --webcam --interval 1.0
```

---

## 4. API Endpoints Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/telemetry/frame` | Ingests raw binary JPEG frame from ESP32-CAM / simulator. Runs inference and broadcasts over WebSockets. |
| `GET` | `/api/v1/telemetry/latest` | Returns the most recent JSON detection metadata, boxes, and confidence. |
| `GET` | `/api/v1/telemetry/latest/frame` | Returns the most recent annotated JPEG image. |
| `GET` | `/api/v1/inventory/summary` | Returns active counts for target lab classes (`3d_printer`, `dell_monitor`, etc.). |
| `WS` | `/api/v1/ws/stream` | Full-duplex WebSocket stream feeding the Next.js dashboard. |
| `GET` | `/health` | Server status, model loaded state, active WebSocket clients, and latency. |
