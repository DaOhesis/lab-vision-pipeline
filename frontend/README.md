# Next.js Real-Time Monitoring Dashboard (`frontend/`)

This directory contains the Next.js 14 real-time IoT monitoring frontend. It connects via WebSockets to the local FastAPI backend to render live camera frames, responsive bounding box overlays, and lab inventory metrics.

---

## 1. Setup & Installation

### Step 1: Install Node.js Dependencies
From the `frontend` directory:
```bash
cd frontend
npm install
```

### Step 2: (Optional) Configure WebSocket Target
By default, the dashboard connects to `ws://localhost:8000/api/v1/ws/stream`. To customize, create a `.env.local` file:
```env
NEXT_PUBLIC_WS_URL=ws://localhost:8000/api/v1/ws/stream
```

---

## 2. Running the Development Server

Start the local Next.js development server:
```bash
npm run dev
```

Open your browser to:
```
http://localhost:3000
```

---

## 3. Key Dashboard Features

- **Live Streaming Viewport**: Visualizes incoming frames directly from the ESP32-CAM or camera simulator.
- **Client-Side Dynamic Overlay**: Renders normalized vector bounding boxes over the frame with interactive confidence sliders and visibility toggles.
- **Equipment Inventory Cards**: Live counters for target lab equipment (`3d_printer`, `dell_monitor`, `microcontroller`, `oscilloscope`, `soldering_station`).
- **Telemetry Indicators**: Displays real-time inference latency (ms), frame delivery rate (FPS), and connection status with automatic reconnection.
- **Detection Event Log**: Chronological audit trail of all localized equipment.
